import streamlit as st
import pandas as pd
from supabase import create_client
import time
import plotly.express as px
from datetime import datetime, timedelta
import requests
import json

# ==============================================================================
# ⚙️ CONFIGURAÇÕES DA IA (CLOUDFLARE)
# ==============================================================================
# Chefe, futuramente coloque isso no secrets.toml para segurança, mas tá na mão:
CF_ACCOUNT_ID = "3baa994dde65370e4085dc8d4ac1e931"
CF_API_TOKEN = "u7UM4xsGySrcEFveL1ah8vi4MdhdwuLOUlekJabC"
CF_MODELO = "@cf/meta/llama-3.1-8b-instruct"
CF_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{CF_MODELO}"
CF_HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json"
}

# ==============================================================================
# ⚙️ VISUAL E ESTILO
# ==============================================================================
st.set_page_config(page_title="Olympikus Manager", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    /* Reset e Fonte */
    .stApp { background-color: #F0F2F6; color: #1F2937; font-family: 'Inter', sans-serif; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #111827; }
    [data-testid="stSidebar"] * { color: #E5E7EB !important; }
    
    /* Cards brancos */
    .card-box {
        background-color: white;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 20px;
    }
    
    /* Métricas */
    .metric-container {
        text-align: center;
        padding: 15px;
        background: #F9FAFB;
        border-radius: 8px;
        border: 1px solid #E5E7EB;
    }
    .metric-label { font-size: 0.85rem; color: #6B7280; text-transform: uppercase; }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #111827; margin-top: 5px; }
    .metric-highlight { color: #2563EB; } 
    
    /* Botões */
    .stButton button {
        border-radius: 8px; font-weight: 600;
        background-color: #2563EB; color: white; border: none;
    }
    .stButton button:hover { background-color: #1D4ED8; }
    
    /* Inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox {
        border-radius: 8px; border: 1px solid #D1D5DB;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔌 CONEXÃO SUPABASE
# ==============================================================================
@st.cache_resource
def init_connection():
    try:
        url = st.secrets.get("SUPABASE_URL", "https://dhihqmxjclyrqkbxshtv.supabase.co")
        key = st.secrets.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRoaWhxbXhqY2x5cnFrYnhzaHR2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI0NTE4MDgsImV4cCI6MjA3ODAyNzgwOH0.jD0RhVMTDHc4Ch9vV_PQ2OlBfyei-PA7VmvEJ1IWi3w")
        if not url or not key: return None
        return create_client(url, key)
    except: return None

supabase = init_connection()

def get_data(table, order_col='created_at'):
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table(table).select("*").order(order_col, desc=True).execute()
        df = pd.DataFrame(res.data)
        
        # Tratamento de datas
        cols_date = ['created_at', 'data_expiracao']
        for col in cols_date:
            if not df.empty and col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    if df[col].dt.tz is not None:
                        df[col] = df[col].dt.tz_localize(None)
        
        if not df.empty and 'created_at' in df.columns:
             df['created_at'] = df['created_at'] - timedelta(hours=3)
        return df
    except: return pd.DataFrame()

def card_metric(label, value, color_class=""):
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">{label}</div>
        <div class="metric-value {color_class}">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def check_status(data_exp):
    if pd.isnull(data_exp): return "S/ Data", "gray"
    hoje = datetime.now()
    delta = (data_exp - hoje).days
    if delta < 0: return "VENCIDO", "#EF4444"
    if delta <= 3: return f"Vence em {delta} dias", "#F59E0B"
    return "Ativo", "#10B981"

# ==============================================================================
# 🧠 FUNÇÃO IA (CLOUDFLARE)
# ==============================================================================
def gerar_relatorio_ia(df_afiliados, df_vendas):
    # Prepara resumo dos dados para não estourar tokens
    resumo_afiliados = []
    
    if not df_afiliados.empty:
        for _, row in df_afiliados.iterrows():
            vendas_af = df_vendas[df_vendas['cupom'] == row['cupom']] if not df_vendas.empty else pd.DataFrame()
            resumo_afiliados.append({
                "nome": row['nome'],
                "cupom": row['cupom'],
                "total_vendas": len(vendas_af),
                "faturamento_gerado": vendas_af['valor_plano'].sum() if not vendas_af.empty else 0
            })
    
    dados_texto = json.dumps(resumo_afiliados, ensure_ascii=False)
    
    prompt_sistema = """
    Você é um Consultor Sênior de um SaaS. Analise os dados dos afiliados e dê um feedback executivo para o dono.
    1. Identifique o TOP performer (quem vendeu mais).
    2. Identifique quem está com performance baixa (zero vendas ou muito pouco).
    3. Dê uma nota de 0 a 10 para a saúde comercial atual.
    4. Seja breve, use Markdown (negrito, tópicos).
    """
    
    payload = {
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Analise estes dados brutos: {dados_texto}"}
        ]
    }
    
    try:
        response = requests.post(CF_URL, headers=CF_HEADERS, json=payload)
        if response.status_code == 200:
            result = response.json()
            return result.get('result', {}).get('response', "IA não retornou texto.")
        else:
            return f"Erro na API Cloudflare: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Erro técnico na requisição: {e}"

# ==============================================================================
# 🔐 LOGIN
# ==============================================================================
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'role': None, 'user': {}})

def login_ui():
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><h1 style='text-align: center;'>Olympikus Manager</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6B7280;'>Sistema Integrado de Gestão</p><br>", unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            tab_parc, tab_adm = st.tabs(["Sou Parceiro", "Sou Admin"])
            
            with tab_parc:
                cupom = st.text_input("Seu Cupom de Acesso").strip().upper()
                if st.button("Acessar Painel", use_container_width=True):
                    if not supabase: st.error("Erro de conexão"); return
                    res = supabase.table("afiliados").select("*").eq("cupom", cupom).execute()
                    if res.data:
                        st.session_state.update({'logged_in': True, 'role': 'afiliado', 'user': res.data[0]})
                        st.rerun()
                    else: st.error("Cupom não encontrado.")
            
            with tab_adm:
                senha = st.text_input("Senha Administrativa", type="password")
                if st.button("Entrar Admin", use_container_width=True):
                    senha_admin = st.secrets.get("ADMIN_PASSWORD", "170905@Ju")
                    if senha == senha_admin:
                        st.session_state.update({'logged_in': True, 'role': 'admin'})
                        st.rerun()
                    else: st.error("Senha incorreta.")
            st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 🛡️ ADMIN PANEL
# ==============================================================================
def admin_panel():
    with st.sidebar:
        st.header("Admin Panel")
        nav = st.radio("Navegação", ["Dashboard", "Gerenciar Parceiros", "Base de Clientes", "Financeiro"], label_visibility="collapsed")
        st.divider()
        if st.button("Sair do Sistema"):
            st.session_state.clear()
            st.rerun()

    # Carrega dados
    df_vendas = get_data('vendas')
    df_afiliados = get_data('afiliados')
    df_saques = get_data('saques')

    # --- 1. DASHBOARD ---
    if nav == "Dashboard":
        st.title("Visão Geral")
        
        # Filtros
        col_f1, col_f2 = st.columns([4, 1])
        with col_f2:
            dias = st.selectbox("Período", [7, 30, 90, 365], index=1)
            
        data_corte = datetime.now() - timedelta(days=dias)
        df_filt = df_vendas[df_vendas['created_at'] >= data_corte] if not df_vendas.empty else df_vendas
        
        # KPIs
        fat = df_filt['valor_plano'].sum() if not df_filt.empty else 0
        comissoes = df_filt['valor_comissao'].sum() if not df_filt.empty else 0
        lucro = fat - comissoes
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: card_metric("Vendas (Período)", len(df_filt))
        with c2: card_metric("Faturamento", f"R$ {fat:,.0f}", "metric-highlight")
        with c3: card_metric("Comissões Pagas", f"R$ {comissoes:,.0f}")
        with c4: card_metric("Lucro Líquido", f"R$ {lucro:,.0f}", "metric-highlight")

        # --- ÁREA DE INTELIGÊNCIA ARTIFICIAL ---
        st.markdown("---")
        st.subheader("🤖 IA Cloudflare - Raio-X da Operação")
        
        col_ia_1, col_ia_2 = st.columns([1, 3])
        with col_ia_1:
             st.info("Modelo: Llama 3.1 8B")
             if st.button("⚡ Gerar Relatório Agora", use_container_width=True):
                with st.spinner("Consultando Llama 3 na Cloudflare..."):
                    relatorio = gerar_relatorio_ia(df_afiliados, df_vendas)
                    if "Erro" not in relatorio:
                        st.session_state['last_report'] = relatorio
                        st.success("Análise concluída!")
                    else:
                        st.error(relatorio)
        
        with col_ia_2:
            if 'last_report' in st.session_state:
                st.markdown(st.session_state['last_report'])
            else:
                st.markdown("*O relatório de inteligência aparecerá aqui após clicar no botão.*")

        # Gráfico
        st.markdown("---")
        st.markdown("### Evolução Diária")
        if not df_filt.empty:
            daily = df_filt.groupby(df_filt['created_at'].dt.date)['valor_plano'].sum().reset_index()
            fig = px.bar(daily, x='created_at', y='valor_plano', color_discrete_sequence=['#2563EB'])
            fig.update_layout(plot_bgcolor='white', margin=dict(t=10,l=10,r=10,b=10))
            st.plotly_chart(fig, use_container_width=True)

    # --- 2. GERENCIAR PARCEIROS ---
    elif nav == "Gerenciar Parceiros":
        st.title("Gestão de Parceiros")
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.markdown("### 📋 Lista de Afiliados")
            if not df_afiliados.empty:
                display_data = []
                for idx, row in df_afiliados.iterrows():
                    vendas_afiliado = df_vendas[df_vendas['cupom'] == row['cupom']] if not df_vendas.empty else pd.DataFrame()
                    total_vendas = len(vendas_afiliado)
                    comissao_total = vendas_afiliado['valor_comissao'].sum() if not vendas_afiliado.empty else 0
                    
                    saques_af = df_saques[(df_saques['cupom'] == row['cupom']) & (df_saques['status'] != 'Rejeitado')] if not df_saques.empty else pd.DataFrame()
                    pago = saques_af['valor'].sum() if not saques_af.empty else 0
                    saldo = comissao_total - pago
                    
                    display_data.append({
                        "ID": row['id'],
                        "Nome": row['nome'],
                        "Cupom": row['cupom'],
                        "Vendas": total_vendas,
                        "Saldo Atual": f"R$ {saldo:.2f}"
                    })
                
                df_display = pd.DataFrame(display_data)
                st.dataframe(df_display, hide_index=True, use_container_width=True)
                
                with st.expander("🗑️ Excluir Parceiro"):
                    c_del1, c_del2 = st.columns([3, 1])
                    id_to_del = c_del1.number_input("ID para Excluir", min_value=0, step=1)
                    if c_del2.button("Confirmar Exclusão"):
                        supabase.table("afiliados").delete().eq("id", id_to_del).execute()
                        st.success("Removido.")
                        time.sleep(1)
                        st.rerun()
            else: st.info("Nenhum parceiro cadastrado.")
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.markdown("### ➕ Novo Parceiro")
            with st.form("add_affiliate"):
                nome = st.text_input("Nome Completo")
                cupom = st.text_input("CUPOM (Único)").upper()
                whats = st.text_input("WhatsApp")
                if st.form_submit_button("Cadastrar", use_container_width=True):
                    try:
                        supabase.table("afiliados").insert({"nome": nome, "cupom": cupom, "whatsapp": whats}).execute()
                        st.success("Sucesso!")
                        st.rerun()
                    except: st.error("Erro: Cupom já existe.")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. BASE DE CLIENTES ---
    elif nav == "Base de Clientes":
        st.title("Base de Clientes")
        
        with st.expander("➕ Adicionar Novo Cliente", expanded=False):
            with st.form("add_client"):
                c1, c2, c3 = st.columns(3)
                nome = c1.text_input("Nome do Cliente")
                valor = c2.number_input("Valor do Plano", value=35.0)
                
                lista_afiliados = ["Venda Direta (Sem Afiliado)"] + [f"{r['nome']} ({r['cupom']})" for i, r in df_afiliados.iterrows()] if not df_afiliados.empty else ["Venda Direta"]
                afiliado_sel = c3.selectbox("Vincular a Parceiro", lista_afiliados)
                
                if st.form_submit_button("Registrar Cliente"):
                    cupom_final = None
                    comissao = 0.0
                    if "Sem Afiliado" not in afiliado_sel:
                        cupom_final = afiliado_sel.split("(")[-1].replace(")", "")
                        comissao = 15.0 
                    
                    data_exp = datetime.now() + timedelta(days=30)
                    supabase.table("vendas").insert({
                        "nome_cliente": nome,
                        "valor_plano": valor,
                        "cupom": cupom_final,
                        "valor_comissao": comissao,
                        "data_expiracao": data_exp.strftime('%Y-%m-%d'),
                        "status": "Ativo"
                    }).execute()
                    st.success("Cliente adicionado!")
                    time.sleep(1)
                    st.rerun()

        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        search = st.text_input("🔍 Buscar Cliente por nome...", "")
        
        if not df_vendas.empty:
            df_show = df_vendas[df_vendas['nome_cliente'].str.contains(search, case=False, na=False)] if search else df_vendas
            
            cols = st.columns([1, 2, 2, 2, 2, 1])
            cols[0].markdown("**ID**")
            cols[1].markdown("**Cliente**")
            cols[2].markdown("**Status**")
            cols[3].markdown("**Vencimento**")
            cols[4].markdown("**Afiliado**")
            cols[5].markdown("**Ação**")
            st.divider()
            
            for i, row in df_show.iterrows():
                status_txt, status_cor = check_status(row['data_expiracao']) if 'data_expiracao' in row else ("-", "gray")
                with st.container():
                    c = st.columns([1, 2, 2, 2, 2, 1])
                    c[0].write(f"#{row['id']}")
                    c[1].write(row['nome_cliente'])
                    c[2].markdown(f"<span style='color:{status_cor}; font-weight:bold'>{status_txt}</span>", unsafe_allow_html=True)
                    c[3].write(row['data_expiracao'].strftime('%d/%m/%Y') if pd.notnull(row.get('data_expiracao')) else "-")
                    c[4].write(row['cupom'] if row['cupom'] else "Direta")
                    
                    if c[5].button("🗑️", key=f"del_cli_{row['id']}"):
                        supabase.table("vendas").delete().eq("id", row['id']).execute()
                        st.rerun()
                st.divider()
        else: st.info("Sem clientes.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 4. FINANCEIRO ---
    elif nav == "Financeiro":
        st.title("Financeiro & Pagamentos")
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.subheader("🔔 Solicitações Pendentes")
            
            pendentes = df_saques[df_saques['status'] == 'Pendente'] if not df_saques.empty else pd.DataFrame()
            if not pendentes.empty:
                for i, row in pendentes.iterrows():
                    with st.container():
                        pc = st.columns([3, 1, 1])
                        pc[0].markdown(f"**{row['cupom']}** solicitou **R$ {row['valor']:.2f}**<br><span style='font-size:12px;color:grey'>Chave: {row.get('comprovante', '-')}</span>", unsafe_allow_html=True)
                        if pc[1].button("✅ Pagar", key=f"pay_{row['id']}"):
                            supabase.table("saques").update({"status": "Pago"}).eq("id", row['id']).execute()
                            st.success("Pago!")
                            time.sleep(0.5)
                            st.rerun()
                        if pc[2].button("❌ Negar", key=f"deny_{row['id']}"):
                            supabase.table("saques").update({"status": "Rejeitado"}).eq("id", row['id']).execute()
                            st.rerun()
                        st.divider()
            else: st.info("Nenhuma solicitação de saque pendente.")
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
             st.markdown('<div class="card-box">', unsafe_allow_html=True)
             st.subheader("Histórico Recente")
             if not df_saques.empty:
                 historico = df_saques[df_saques['status'] != 'Pendente'].head(10)
                 st.dataframe(historico[['cupom', 'valor', 'status']], hide_index=True)
             st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 🚀 AFFILIATE PANEL
# ==============================================================================
def affiliate_panel():
    user = st.session_state['user']
    cupom = user['cupom']
    
    with st.sidebar:
        st.header(f"Olá, {user['nome'].split()[0]}")
        st.info(f"Cupom Ativo: {cupom}")
        nav = st.radio("Menu", ["Dashboard", "Material de Apoio"], label_visibility="collapsed")
        st.divider()
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()

    df_vendas = get_data('vendas')
    minhas_vendas = df_vendas[df_vendas['cupom'] == cupom] if not df_vendas.empty else pd.DataFrame()

    if nav == "Dashboard":
        st.title("Meu Painel")
        
        vendas_ativas = minhas_vendas[minhas_vendas['status'] == 'Ativo'] if not minhas_vendas.empty else pd.DataFrame()
        comissao_total = vendas_ativas['valor_comissao'].sum() if not vendas_ativas.empty else 0
        
        df_saques = get_data('saques')
        meus_saques = df_saques[(df_saques['cupom'] == cupom) & (df_saques['status'] != 'Rejeitado')] if not df_saques.empty else pd.DataFrame()
        ja_recebido = meus_saques['valor'].sum() if not meus_saques.empty else 0
        a_receber = comissao_total - ja_recebido
        
        c1, c2, c3 = st.columns(3)
        with c1: card_metric("Clientes Ativos", len(vendas_ativas))
        with c2: card_metric("Saldo a Receber", f"R$ {a_receber:.2f}", "metric-highlight")
        with c3: card_metric("Total Ganho", f"R$ {comissao_total:.2f}")
        
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.subheader("💸 Solicitar Saque")
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            valor_saque = st.number_input("Valor para sacar (R$)", min_value=0.0, max_value=float(a_receber) if a_receber > 0 else 0.0, step=10.0)
            chave_pix = st.text_input("Sua Chave PIX")
        with col_s2:
            st.write("") 
            st.write("")
            if st.button("Solicitar Pagamento", use_container_width=True, disabled=(a_receber < 10)):
                if valor_saque > 0 and chave_pix:
                    supabase.table("saques").insert({"cupom": cupom, "valor": valor_saque, "status": "Pendente", "comprovante": chave_pix}).execute()
                    st.success("Solicitação enviada!")
                    time.sleep(1)
                    st.rerun()
                else: st.warning("Preencha valor e PIX.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("### Meus Clientes")
        if not minhas_vendas.empty:
            display_cli = []
            for i, r in minhas_vendas.iterrows():
                sts_txt, _ = check_status(r.get('data_expiracao'))
                display_cli.append({
                    "Cliente": r['nome_cliente'],
                    "Status": sts_txt,
                    "Vencimento": r['data_expiracao'].strftime('%d/%m') if pd.notnull(r.get('data_expiracao')) else "-",
                    "Comissão": f"R$ {r['valor_comissao']:.2f}"
                })
            st.dataframe(pd.DataFrame(display_cli), hide_index=True, use_container_width=True)
        else: st.info("Você ainda não possui vendas ativas.")

    elif nav == "Material de Apoio":
        st.title("📢 Marketing & Arquivos")
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown("### Acesso ao Drive")
        st.link_button("📂 Acessar Pasta do Google Drive", "https://drive.google.com/", use_container_width=True)
        st.divider()
        st.markdown("#### Link Rápido de Venda")
        texto_zap = f"Olá, gostaria de contratar com o cupom {cupom}"
        link_zap = f"https://wa.me/5511999999999?text={texto_zap.replace(' ', '%20')}"
        st.code(link_zap)
        st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 🚦 MAIN ROUTER
# ==============================================================================
if not st.session_state['logged_in']:
    login_ui()
else:
    if st.session_state['role'] == 'admin':
        admin_panel()
    elif st.session_state['role'] == 'afiliado':
        affiliate_panel()
