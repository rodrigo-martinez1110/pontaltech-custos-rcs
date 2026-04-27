import streamlit as st
import pandas as pd
import io

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Calculadora de Custos RCS & SMS",
    page_icon="📱",
    layout="wide",
)

# ── Preços ──────────────────────────────────────────────────────────────────
# Preços em centavos: 0.105 centavos de RCS e 0.05 centavos de SMS
# 1 centavo = R$ 0,01  →  0.105 centavos = R$ 0,00105
PRECO_RCS = 0.105 / 100   # R$ 0,00105
PRECO_SMS = 0.05  / 100   # R$ 0,0005

# ── Cabeçalho ───────────────────────────────────────────────────────────────
st.title("📱 Calculadora de Custos — RCS & SMS")
st.markdown(
    """
    Faça upload do relatório de campanhas para calcular o custo total de envios.

    | Tipo | Custo unitário |
    |------|---------------|
    | RCS  | R$ 0,00105 / mensagem |
    | SMS  | R$ 0,0005 / mensagem  |
    """
)

st.divider()

# ── Upload ───────────────────────────────────────────────────────────────────
arquivo = st.file_uploader(
    "Selecione o arquivo CSV de campanhas",
    type=["csv"],
    help="Arquivo exportado do painel de campanhas (separador: ponto-e-vírgula)",
)

if arquivo is None:
    st.info("⬆️ Aguardando upload do arquivo CSV...")
    st.stop()

# ── Leitura ──────────────────────────────────────────────────────────────────
try:
    df = pd.read_csv(arquivo, sep=";", encoding="utf-8")
except UnicodeDecodeError:
    arquivo.seek(0)
    df = pd.read_csv(arquivo, sep=";", encoding="latin-1")

colunas_necessarias = {"TOTAL RCS ENVIADO", "TOTAL SMS ENVIADO"}
if not colunas_necessarias.issubset(df.columns):
    st.error(
        f"❌ Colunas esperadas não encontradas no arquivo.\n\n"
        f"Necessárias: `{', '.join(colunas_necessarias)}`\n\n"
        f"Encontradas: `{', '.join(df.columns.tolist())}`"
    )
    st.stop()

# ── Conversão numérica ────────────────────────────────────────────────────────
df["TOTAL RCS ENVIADO"] = pd.to_numeric(df["TOTAL RCS ENVIADO"], errors="coerce").fillna(0).astype(int)
df["TOTAL SMS ENVIADO"] = pd.to_numeric(df["TOTAL SMS ENVIADO"], errors="coerce").fillna(0).astype(int)

# ── Cálculo por linha ─────────────────────────────────────────────────────────
df["CUSTO RCS (R$)"]   = (df["TOTAL RCS ENVIADO"] * PRECO_RCS).round(2)
df["CUSTO SMS (R$)"]   = (df["TOTAL SMS ENVIADO"] * PRECO_SMS).round(2)
df["CUSTO TOTAL (R$)"] = (df["CUSTO RCS (R$)"] + df["CUSTO SMS (R$)"]).round(2)

# ── Totais gerais ─────────────────────────────────────────────────────────────
total_rcs_msgs  = int(df["TOTAL RCS ENVIADO"].sum())
total_sms_msgs  = int(df["TOTAL SMS ENVIADO"].sum())
total_custo_rcs = df["CUSTO RCS (R$)"].sum()
total_custo_sms = df["CUSTO SMS (R$)"].sum()
total_geral     = total_custo_rcs + total_custo_sms

# ── KPIs ──────────────────────────────────────────────────────────────────────
st.subheader("📊 Resumo Geral")

col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

col1.metric("📨 Mensagens RCS Enviadas", f"{total_rcs_msgs:,}".replace(",", "."))
col2.metric("📩 Mensagens SMS Enviadas", f"{total_sms_msgs:,}".replace(",", "."))
col3.metric("📬 Total de Mensagens",     f"{total_rcs_msgs + total_sms_msgs:,}".replace(",", "."))

col4.metric("💸 Custo RCS",   f"R$ {total_custo_rcs:,.4f}".replace(",", "X").replace(".", ",").replace("X", "."))
col5.metric("💸 Custo SMS",   f"R$ {total_custo_sms:,.4f}".replace(",", "X").replace(".", ",").replace("X", "."))
col6.metric("💰 Custo Total", f"R$ {total_geral:,.4f}".replace(",", "X").replace(".", ",").replace("X", "."), delta=None)

st.divider()

# ── Filtros ───────────────────────────────────────────────────────────────────
st.subheader("🔍 Detalhamento por Campanha")

with st.expander("Filtros", expanded=False):
    col_f1, col_f2 = st.columns(2)

    if "CONTA" in df.columns:
        contas = ["Todas"] + sorted(df["CONTA"].dropna().unique().tolist())
        conta_sel = col_f1.selectbox("Conta", contas)
    else:
        conta_sel = "Todas"

    if "TIPO DA CAMPANHA" in df.columns:
        tipos = ["Todos"] + sorted(df["TIPO DA CAMPANHA"].dropna().unique().tolist())
        tipo_sel = col_f2.selectbox("Tipo de Campanha", tipos)
    else:
        tipo_sel = "Todos"

df_filtrado = df.copy()
if conta_sel != "Todas" and "CONTA" in df.columns:
    df_filtrado = df_filtrado[df_filtrado["CONTA"] == conta_sel]
if tipo_sel != "Todos" and "TIPO DA CAMPANHA" in df.columns:
    df_filtrado = df_filtrado[df_filtrado["TIPO DA CAMPANHA"] == tipo_sel]

# ── Colunas para exibição ─────────────────────────────────────────────────────
colunas_exibir = []
for c in ["NOME CAMPANHA", "DATA CRIACAO DA CAMPANHA", "TIPO DA CAMPANHA", "CONTA"]:
    if c in df_filtrado.columns:
        colunas_exibir.append(c)

colunas_exibir += ["TOTAL RCS ENVIADO", "CUSTO RCS (R$)", "TOTAL SMS ENVIADO", "CUSTO SMS (R$)", "CUSTO TOTAL (R$)"]

df_exibir = df_filtrado[colunas_exibir].copy()

# Formatação monetária só para exibição
def fmt_brl(v):
    return f"R$ {v:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.dataframe(
    df_exibir.style.format({
        "CUSTO RCS (R$)":   fmt_brl,
        "CUSTO SMS (R$)":   fmt_brl,
        "CUSTO TOTAL (R$)": fmt_brl,
    }),
    use_container_width=True,
    hide_index=True,
)

# ── Subtotais do filtro ────────────────────────────────────────────────────────
if conta_sel != "Todas" or tipo_sel != "Todos":
    st.caption(
        f"**Subtotal filtrado** → "
        f"RCS: {int(df_filtrado['TOTAL RCS ENVIADO'].sum()):,} msgs | "
        f"SMS: {int(df_filtrado['TOTAL SMS ENVIADO'].sum()):,} msgs | "
        f"Custo: R$ {df_filtrado['CUSTO TOTAL (R$)'].sum():,.4f}"
        .replace(",", "X").replace(".", ",").replace("X", ".")
    )

st.divider()

# ── Download ───────────────────────────────────────────────────────────────────
st.subheader("⬇️ Exportar Resultado")

csv_out = df[colunas_exibir].copy()
buffer = io.BytesIO()
csv_out.to_csv(buffer, index=False, sep=";", encoding="utf-8-sig")
buffer.seek(0)

st.download_button(
    label="📥 Baixar CSV com custos calculados",
    data=buffer,
    file_name="custos_campanhas.csv",
    mime="text/csv",
)

st.caption("Preços aplicados: RCS = R$ 0,00105/msg · SMS = R$ 0,0005/msg")
