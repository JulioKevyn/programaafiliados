import streamlit as st
import pandas as pd
from supabase import create_client

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Portal do Afiliado", page_icon="💰")

# --- CONEXÃO COM SUPABASE ---
# O Streamlit busca isso nos "Segredos" que vamos configurar no passo 4
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except:
    st.error("Erro na conexão. Verifique as chaves no Streamlit Cloud.")
    st.stop()

# --- INTERFACE ---
st.title("🚀 Área do Parceiro")
st.markdown("Entre com seu cupom para ver suas vendas.")

# --- LOGIN ---
cupom_login = st.text_input("Seu Cupom:", placeholder="Ex: JULIO10").upper().strip()

if cupom_login:
    # Busca no banco
    response = supabase.table("vendas").select("*").eq("cupom", cupom_login).execute()
    dados = response.data

    if dados:
        df = pd.DataFrame(dados)
        
        # Filtra ativos
        ativos = df[df['status'] == 'Ativo']
        
        # Métricas
        col1, col2 = st.columns(2)
        col1.metric("Clientes Ativos", len(ativos))
        col2.metric("A Receber", f"R$ {ativos['valor_comissao'].sum():.2f}")
        
        st.divider()
        st.subheader("Extrato de Clientes")
        # Mostra a tabela limpa
        st.dataframe(ativos[['created_at', 'nome_cliente', 'status']], hide_index=True)
    else:
        st.warning("Nenhuma venda encontrada para este cupom.")
