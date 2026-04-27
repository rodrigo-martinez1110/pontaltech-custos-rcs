import streamlit as st
import pandas as pd
import io

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Calculadora de Custos RCS & SMS",
    page_icon="📱",
    layout="wide",
)

# ── Preços (em centavos → convertido para R$) ────────────────────────────────
PRECO_RCS = 0.105 / 100   # 0,105 centavos = R$ 0,00105
PRECO_SMS = 0.05  / 100   # 0,05 centavos  = R$ 0,0005

# ── Helpers ──────────────────────────────────────────────────────────────────
def fmt_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_num(v):
    return f"{int(v):,}".replace(",", ".")

def ler_csv(arquivo, sep=";"):
    try:
        return pd.read_csv(arquivo, sep=sep, encoding="utf-8")
    except UnicodeDecodeError:
        arquivo.seek(0)
        return pd.read_csv(arquivo, sep=sep, encoding="latin-1")

# ── Cabeçalho ────────────────────────────────────────────────────────────────
st.title("📱 Calculadora de Custos — RCS & SMS")
st.markdown("""
| Tipo | Custo unitário |
|------|---------------|
| RCS  | 0,105 centavos → R$ 0,00105 / mensagem |
| SMS  | 0,05 centavos  → R$ 0,0005  / mensagem |
""")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 1 — Relatório RCS (com SMS embutido quando Conta = RCS Single)
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📂 Relatório RCS (campanhas)")
arq_rcs = st.file_uploader(
    "Arquivo sintético de campanhas RCS (.csv, separador `;`)",
    type=["csv"],
    key="rcs",
)

df_rcs = None
colunas_exibir_rcs = []
total_rcs_msgs = total_sms_rcs_msgs = 0
custo_rcs = custo_sms_via_rcs = 0.0

if arq_rcs:
    df_rcs = ler_csv(arq_rcs, sep=";")

    cols_ok = {"TOTAL RCS ENVIADO", "TOTAL SMS ENVIADO"}
    if not cols_ok.issubset(df_rcs.columns):
        st.error(f"❌ Colunas esperadas não encontradas: {cols_ok - set(df_rcs.columns)}")
        df_rcs = None
    else:
        df_rcs["TOTAL RCS ENVIADO"] = pd.to_numeric(df_rcs["TOTAL RCS ENVIADO"], errors="coerce").fillna(0).astype(int)
        df_rcs["TOTAL SMS ENVIADO"] = pd.to_numeric(df_rcs["TOTAL SMS ENVIADO"], errors="coerce").fillna(0).astype(int)

        df_rcs["CUSTO RCS (R$)"]   = (df_rcs["TOTAL RCS ENVIADO"] * PRECO_RCS).round(2)
        df_rcs["CUSTO SMS (R$)"]   = (df_rcs["TOTAL SMS ENVIADO"] * PRECO_SMS).round(2)
        df_rcs["CUSTO TOTAL (R$)"] = (df_rcs["CUSTO RCS (R$)"] + df_rcs["CUSTO SMS (R$)"]).round(2)

        total_rcs_msgs     = int(df_rcs["TOTAL RCS ENVIADO"].sum())
        total_sms_rcs_msgs = int(df_rcs["TOTAL SMS ENVIADO"].sum())
        custo_rcs          = round(df_rcs["CUSTO RCS (R$)"].sum(), 2)
        custo_sms_via_rcs  = round(df_rcs["CUSTO SMS (R$)"].sum(), 2)

        for c in ["NOME CAMPANHA", "DATA CRIACAO DA CAMPANHA", "TIPO DA CAMPANHA", "CONTA"]:
            if c in df_rcs.columns:
                colunas_exibir_rcs.append(c)
        colunas_exibir_rcs += ["TOTAL RCS ENVIADO", "CUSTO RCS (R$)", "TOTAL SMS ENVIADO", "CUSTO SMS (R$)", "CUSTO TOTAL (R$)"]

        with st.expander("Ver detalhamento por campanha RCS", expanded=False):
            st.dataframe(
                df_rcs[colunas_exibir_rcs].style.format({
                    "CUSTO RCS (R$)":   fmt_brl,
                    "CUSTO SMS (R$)":   fmt_brl,
                    "CUSTO TOTAL (R$)": fmt_brl,
                }),
                use_container_width=True,
                hide_index=True,
            )
else:
    st.info("⬆️ Aguardando upload do relatório RCS...")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 2 — Relatório SMS Sintético (somente linhas com Conta vazia)
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📂 Relatório SMS Sintético")
st.caption("Apenas linhas com coluna **Conta vazia** são consideradas — evita duplicar SMS já contabilizados no relatório RCS.")

arq_sms = st.file_uploader(
    "Arquivo sintético de SMS (.csv, separador `TAB`)",
    type=["csv"],
    key="sms",
)

df_sms_filtrado = None
colunas_exibir_sms = []
total_sms_puro_msgs = 0
custo_sms_puro = 0.0

if arq_sms:
    df_sms = ler_csv(arq_sms, sep="\t")

    if "Conta" not in df_sms.columns or "Quantidade" not in df_sms.columns:
        st.error(f"❌ Colunas 'Conta' e/ou 'Quantidade' não encontradas. Encontradas: {df_sms.columns.tolist()}")
    else:
        # Apenas linhas onde Conta está vazia (NaN ou string vazia/espaços)
        mask_vazia = df_sms["Conta"].isna() | (df_sms["Conta"].astype(str).str.strip() == "")
        df_sms_filtrado = df_sms[mask_vazia].copy()

        df_sms_filtrado["Quantidade"] = pd.to_numeric(df_sms_filtrado["Quantidade"], errors="coerce").fillna(0).astype(int)
        df_sms_filtrado["CUSTO SMS (R$)"] = (df_sms_filtrado["Quantidade"] * PRECO_SMS).round(2)

        total_sms_puro_msgs = int(df_sms_filtrado["Quantidade"].sum())
        custo_sms_puro      = round(df_sms_filtrado["CUSTO SMS (R$)"].sum(), 2)

        total_linhas = len(df_sms)
        total_ignoradas = total_linhas - len(df_sms_filtrado)

        st.caption(
            f"📋 {total_linhas} linhas no arquivo · "
            f"✅ {len(df_sms_filtrado)} com Conta vazia (SMS puro) · "
            f"⏭️ {total_ignoradas} ignoradas (Conta preenchida = já contabilizadas no RCS)"
        )

        if len(df_sms_filtrado) > 0:
            for c in ["Mailing", "Data", "Usuario", "Quantidade", "Enviadas", "CUSTO SMS (R$)"]:
                if c in df_sms_filtrado.columns:
                    colunas_exibir_sms.append(c)

            with st.expander("Ver detalhamento SMS puro (Conta vazia)", expanded=False):
                st.dataframe(
                    df_sms_filtrado[colunas_exibir_sms].style.format({
                        "CUSTO SMS (R$)": fmt_brl,
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.warning("⚠️ Nenhuma linha com Conta vazia encontrada neste arquivo.")
else:
    st.info("⬆️ Aguardando upload do relatório SMS sintético...")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# RESUMO CONSOLIDADO
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📊 Resumo Consolidado")

custo_sms_total = round(custo_sms_via_rcs + custo_sms_puro, 2)
custo_geral     = round(custo_rcs + custo_sms_total, 2)

col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

col1.metric("📨 Msgs RCS",                 fmt_num(total_rcs_msgs))
col2.metric("📩 Msgs SMS (via RCS)",       fmt_num(total_sms_rcs_msgs),
            help="SMS do relatório RCS onde Conta = RCS Single")
col3.metric("📩 Msgs SMS (sintético puro)", fmt_num(total_sms_puro_msgs),
            help="SMS do arquivo sintético com Conta vazia")

col4.metric("💸 Custo RCS",    fmt_brl(custo_rcs))
col5.metric("💸 Custo SMS",    fmt_brl(custo_sms_total),
            help=f"RCS report: {fmt_brl(custo_sms_via_rcs)} + Sintético puro: {fmt_brl(custo_sms_puro)}")
col6.metric("💰 Custo Total",  fmt_brl(custo_geral))

st.caption(
    f"SMS detalhado → Via relatório RCS: {fmt_brl(custo_sms_via_rcs)} ({fmt_num(total_sms_rcs_msgs)} msgs)  |  "
    f"Via sintético puro (Conta vazia): {fmt_brl(custo_sms_puro)} ({fmt_num(total_sms_puro_msgs)} msgs)"
)

st.divider()

# ── Downloads ─────────────────────────────────────────────────────────────────
st.subheader("⬇️ Exportar")
col_dl1, col_dl2 = st.columns(2)

if df_rcs is not None and colunas_exibir_rcs:
    buf1 = io.BytesIO()
    df_rcs[colunas_exibir_rcs].to_csv(buf1, index=False, sep=";", encoding="utf-8-sig")
    buf1.seek(0)
    col_dl1.download_button("📥 CSV Campanhas RCS", buf1, "custos_rcs.csv", "text/csv")

if df_sms_filtrado is not None and len(df_sms_filtrado) > 0 and colunas_exibir_sms:
    buf2 = io.BytesIO()
    df_sms_filtrado[colunas_exibir_sms].to_csv(buf2, index=False, sep=";", encoding="utf-8-sig")
    buf2.seek(0)
    col_dl2.download_button("📥 CSV SMS Puro", buf2, "custos_sms_puro.csv", "text/csv")

st.caption(
    "Preços: RCS = 0,105 centavos/msg (R$ 0,00105) · SMS = 0,05 centavos/msg (R$ 0,0005) · "
    "SMS sintético: apenas linhas com Conta vazia · Valores arredondados para 2 casas decimais"
)
