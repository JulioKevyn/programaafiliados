import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
from datetime import datetime, timedelta
import time

# ==============================================================================
# CONFIG
# ==============================================================================
st.set_page_config("OLYMPIKUS IPTV", "⚡", layout="wide")

# ==============================================================================
# THEME
# ==============================================================================
st.markdown("""
<style>
.stApp { background:#0B0F1A; color:#E6EDF3; }
header, footer { display:none; }

.sidebar { background:#0E1426; }

.card {
    background:#12182B;
    border:1px solid #1F2A44;
    border-radius:14px;
    padding:20px;
}
.card h3 { margin:0; font-size:13px; color:#8B949E; }
.card h1 { margin:5px 0 0 0; }

.blue { color:#2F81F7; }
.green { color:#3FB950; }
.gold { color:#F5C542; }
.red { color:#F85149; }

.stButton button {
    background:#2F81F7;
    border-radius:8px;
    font-weight:700;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# DATABASE
# ==============================================================================
@st.cache_resource
def db():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

supabase = db()

def load(table):
    r = supabase.table(table).select("*").execute()
    df = pd.DataFrame(r.data)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"]) - timedelta(hours=3)
    return df

# ==============================================================================
# AUTH STATE
# ==============================================================================
if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = None
    st.session_state.user = None

# ==============================================================================
# LOGIN
# ==============================================================================
def login():
    st.markdown("<h1 style='text-align:center'>⚡ OLYMPIKUS IPTV</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#8B949E'>Sistema Profissional de Gestão</p>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🤝 Afiliado", "🛡 Admin"])

    with tab1:
        cupom = st.text_input("Cupom").upper()
        if st.button("Entrar"):
            r = supabase.table("afiliados").select("*").eq("cupom", cupom).execute()
            if r.data:
                st.session_state.auth = True
                st.session_state.role = "afiliado"
                st.session_state.user = r.data[0]
                st.rerun()
            else:
                st.error("Cupom inválido")

    with tab2:
        senha = st.text_input("Senha Master", type="password")
        if st.button("Entrar como Admin"):
            if senha == st.secrets["ADMIN_PASSWORD"]:
                st.session_state.auth = True
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Senha incorreta")

# ==============================================================================
# ADMIN DASHBOARD
# ==============================================================================
def admin():
    vendas = load("vendas")
    afiliados = load("afiliados")

    ativos = vendas[vendas.status == "Ativo"]
    cancelados = vendas[vendas.status == "Cancelado"]

    faturamento = ativos.valor_plano.sum()
    comissao = ativos.valor_comissao.sum()
    lucro = faturamento - comissao

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.markdown(f"<div class='card'><h3>Vendas</h3><h1>{len(vendas)}</h1></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><h3>Ativos</h3><h1 class='green'>{len(ativos)}</h1></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><h3>Cancelados</h3><h1 class='red'>{len(cancelados)}</h1></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card'><h3>Faturamento</h3><h1>R$ {faturamento:.0f}</h1></div>", unsafe_allow_html=True)
    c5.markdown(f"<div class='card'><h3>Lucro</h3><h1 class='gold'>R$ {lucro:.0f}</h1></div>", unsafe_allow_html=True)

    st.markdown("### 📈 Receita por Dia")
    chart = ativos.groupby(ativos.created_at.dt.date)["valor_plano"].sum().reset_index()
    st.plotly_chart(px.bar(chart, x="created_at", y="valor_plano"), use_container_width=True)

    st.markdown("### 🏆 Ranking Afiliados")
    rank = ativos.groupby("cupom")["valor_comissao"].sum().reset_index().sort_values("valor_comissao", ascending=False)
    st.dataframe(rank, use_container_width=True)

    if st.sidebar.button("🚪 Sair"):
        st.session_state.auth = False
        st.rerun()

# ==============================================================================
# AFILIADO DASHBOARD
# ==============================================================================
def afiliado():
    user = st.session_state.user
    vendas = load("vendas")
    df = vendas[vendas.cupom == user["cupom"]]

    ativos = df[df.status == "Ativo"]
    saldo = ativos.valor_comissao.sum()

    c1,c2,c3 = st.columns(3)
    c1.markdown(f"<div class='card'><h3>Vendas</h3><h1>{len(df)}</h1></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><h3>Ativos</h3><h1 class='green'>{len(ativos)}</h1></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><h3>Saldo</h3><h1 class='gold'>R$ {saldo:.2f}</h1></div>", unsafe_allow_html=True)

    st.markdown("### 📋 Minhas Vendas")
    st.dataframe(df, use_container_width=True)

    st.markdown("### 📈 Evolução")
    chart = ativos.groupby(ativos.created_at.dt.date)["valor_comissao"].sum().reset_index()
    st.plotly_chart(px.line(chart, x="created_at", y="valor_comissao"), use_container_width=True)

    if st.sidebar.button("🚪 Sair"):
        st.session_state.auth = False
        st.rerun()

# ==============================================================================
# ROUTER
# ==============================================================================
if not st.session_state.auth:
    login()
else:
    admin() if st.session_state.role == "admin" else afiliado()
