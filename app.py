import streamlit as st
import ccxt
import pandas as pd
import time
from PIL import Image
import google.generativeai as genai  # Biblioteca para a IA ler a foto

# 1. CONFIGURAÇÃO DA PÁGINA E IA
st.set_page_config(page_title="Lox Vision Scalper AI", page_icon="📸", layout="wide")
st.title("📸 Lox Vision Scalper AI")
st.subheader("Envie a foto do gráfico e receba a ordem calculada para 1-2 minutos")

# CONFIGURAÇÃO DA CHAVE DA IA (Gratuita no Google AI Studio)
# Para testar, você pode colar sua chave direto aqui ou usar os Secrets do Streamlit
GOOGLE_API_KEY = "AQ.Ab8RN6JaY4pr0D4CwozoRaWntLIJoklEqyZ2Anajad8C8mCzpw" 
genai.configure(api_key=GOOGLE_API_KEY)

# Inicializa o motor de dados de mercado
exchange = ccxt.binance({'enableRateLimit': True})

# 2. PAINEL LATERAL
st.sidebar.header("⚙️ Configurações Operacionais")
crypto_choice = st.sidebar.selectbox(
    "Moeda da Foto:",
    ["Bitcoin (BTC)", "Ethereum (ETH)", "Solana (SOL)", "BNB"]
)

moeda_map = {
    "Bitcoin (BTC)": "BTC/USDT",
    "Ethereum (ETH)": "ETH/USDT",
    "Solana (SOL)": "SOL/USDT",
    "BNB": "BNB/USDT"
}
symbol = moeda_map[crypto_choice]

banca_total = st.sidebar.number_input("Sua Banca ($)", value=1000.0)
risco_por_op = st.sidebar.slider("Risco por Operação (%)", 0.1, 5.0, 1.0)
alvo_gain = st.sidebar.slider("Alvo de Lucro (%)", 0.1, 2.0, 0.4)

# 3. CAMPO DE UPLOAD DA FOTO (Funciona direto pela câmera do celular também)
st.markdown("### 📥 Passo 1: Envie o Print do seu Gráfico")
uploaded_file = st.file_uploader("Tire uma foto ou envie o print da Loxbroker", type=["png", "jpg", "jpeg"])

# 4. CAPTURA DE DADOS DE MERCADO EM SEGUNDO PLANO
def buscar_dados_tempo_real(symbol):
    try:
        # Busca candles de 1 minuto
        candles = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=20)
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Busca Order Book (Fluxo)
        order_book = exchange.fetch_order_book(symbol, limit=10)
        bids = sum([v[1] for v in order_book['bids']])
        asks = sum([v[1] for v in order_book['asks']])
        pressao_compra = (bids / (bids + asks)) * 100 if (bids + asks) > 0 else 50.0
        
        return df['close'].iloc[-1], pressao_compra, df['volume'].iloc[-1]
    except:
        return None, 50.0, 0.0

# 5. PROCESSAMENTO SE A FOTO FOR ENVIADA
if uploaded_file is not None:
    # Mostra a imagem na tela para o usuário confirmar
    image = Image.open(uploaded_file)
    st.image(image, caption="Gráfico Enviado para Análise", width=400)
    
    st.markdown("---")
    st.subheader("🤖 Passo 2: Análise da Inteligência Artificial")
    
    with st.spinner("A IA está analisando os padrões gráficos da sua foto e cruzando com o livro de ofertas..."):
        # Busca os dados exatos do mercado agora para cruzar com a foto
        preco_atual, fluxo_compras, volume_atual = buscar_dados_tempo_real(symbol)
        
        if preco_atual:
            # Cálculos de Gestão de Risco
            dinheiro_em_risco = banca_total * (risco_por_op / 100)
            stop_porcentagem = alvo_gain / 1.5
            tamanho_posicao = dinheiro_em_risco / (stop_porcentagem / 100)
            
            preco_stop_buy = preco_atual * (1 - (stop_porcentagem / 100))
            preco_gain_buy = preco_atual * (1 + (alvo_gain / 100))
            
            preco_stop_sell = preco_atual * (1 + (stop_porcentagem / 100))
            preco_gain_sell = preco_atual * (1 - (alvo_gain / 100))

            # PROMPT PARA A IA DE VISÃO (O que ela deve procurar na imagem)
            prompt = f"""
            Você é um trader especialista em Scalping de 1 minuto. 
            Analise esta imagem do gráfico da corretora para o par {symbol}.
            O preço atual de mercado em tempo real é de ${preco_atual:,.2f} e o fluxo do livro de ofertas indica {fluxo_compras:.1f}% de pressão compradora.
            
            Com base no padrão dos candles na foto (suportes, resistências, tendências visíveis), defina se a probabilidade para os próximos 1 a 2 minutos é de COMPRA (BUY) ou VENDA (SELL).
            
            Responda estritamente neste formato:
            DECISÃO: [Escreva COMPRA ou VENDA ou AGUARDAR]
            MOTIVO VISUAL: [Explique em uma frase curta o padrão que viu na foto]
            """

            # Executa a análise visual se a chave de API estiver configurada
            if GOOGLE_API_KEY != "SUA_API_KEY_AQUI":
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content([prompt, image])
                    texto_ia = response.text
                    
                    # Exibe o resultado na tela de forma organizada
                    st.write("### 📊 Veredito do Especialista:")
                    st.info(texto_ia)
                    
                    # Mostra a boleta de cálculo baseada na decisão do mercado
                    st.markdown("### 📋 Configuração de Gestão para a Ordem:")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Valor do Lote Sugerido:** ${tamanho_posicao:.2f}")
                        st.write(f"**Preço de Entrada:** ${preco_atual:,.2f}")
                    with col2:
                        st.write(f"**Se for COMPRA:** Alvo: ${preco_gain_buy:,.2f} | Stop: ${preco_stop_buy:,.2f}")
                        st.write(f"**Se for VENDA:** Alvo: ${preco_gain_sell:,.2f} | Stop: ${preco_stop_sell:,.2f}")
                        
                except Exception as e:
                    st.error(f"Erro ao processar a imagem com a IA: {e}")
         
