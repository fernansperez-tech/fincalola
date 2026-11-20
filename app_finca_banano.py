import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pandas as pd
from datetime import datetime
import time
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Bananera la Lola S.a", page_icon="🍌", layout="centered")

COLORES_CINTA = ["Amarilla", "Morada", "Roja", "Café", "Negra", "Verde", "Azul", "Blanca"]
LOTES = [f"Lote {i:02d}" for i in range(1, 15)]
HECTAREAS_LOTE = {
    "Lote 01": 3.9, "Lote 02": 4.6, "Lote 03": 4.8, "Lote 04": 7,
    "Lote 05": 7.4, "Lote 06": 7.3, "Lote 07": 5.1, "Lote 08": 6.4,
    "Lote 09": 8.5, "Lote 10": 7.8, "Lote 11": 7.7, "Lote 12": 6.3,
    "Lote 13": 6, "Lote 14": 3.3
}

PARCELEROS_BASE = [
    "Carracedo Daison",
    "Chiquillo libardo",
    "Fernanadez Luis",
    "Cantillo Pedro",
    "Acosta Yeison",
    "Reales Isaac",
    "Gonzales Jose",
    "Felipe Evenildo",
    "Narvaez Osvaldo",
    "Santiago Oscar",
    "Silva Harold",
    "Pantoja Cesar",
    "Osvaldo Castro",
        
    "Otro (Escribir nombre)"
]

CLAVE_ADMIN = "banano2026"
ID_HOJA = "1WnHs71IMeuz9X9sAtJkNYJbR9QJE2QqAKq37-PGsr-0"
NOMBRE_HOJA = "Hoja 1"

if "cola_offline" not in st.session_state:
    st.session_state.cola_offline = []

def conectar_hoja():
    sec = st.secrets["connections"]["gsheets"]
    llave_privada = sec["private_key"].replace("\\n", "\n")
    prefijo = "https" + chr(58) + "//"
    dominio_g = "googleapis.com"
    info_credenciales = {
        "type": "service_account",
        "project_id": sec["project_id"],
        "private_key_id": sec["private_key_id"],
        "private_key": llave_privada,
        "client_email": sec["client_email"],
        "client_id": sec["client_id"],
        "auth_uri": prefijo + "://google.com",
        "token_uri": prefijo + "oauth2." + dominio_g + "/token",
        "auth_provider_x509_cert_url": prefijo + "www." + dominio_g + "/oauth2/v1/certs",
        "client_x509_cert_url": sec.get("client_x509_cert_url", "")
    }
    alcances = [
        prefijo + "www." + dominio_g + "/auth/spreadsheets",
        prefijo + "www." + dominio_g + "/auth/drive"
    ]
    credenciales = Credentials.from_service_account_info(info_credenciales, scopes=alcances)
    gc = gspread.authorize(credenciales)
    sh = gc.open_by_key(ID_HOJA)
    return sh.worksheet(NOMBRE_HOJA)

def cargar_datos():
    try:
        ws = conectar_hoja()
        datos = ws.get_all_records()
        if not datos:
            return pd.DataFrame(columns=["Fecha", "Hora", "Semana", "Lote", "Parcelero", "Color_Cinta", "Racimos", "Estado"])
        return pd.DataFrame(datos)
    except Exception:
        return pd.DataFrame(columns=["Fecha", "Hora", "Semana", "Lote", "Parcelero", "Color_Cinta", "Racimos", "Estado"])

def agregar_filas(lista_registros):
    ws = conectar_hoja()
    filas = []
    for r in lista_registros:
        filas.append([
            r["Fecha"], r["Hora"], int(r["Semana"]), r["Lote"],
            r["Parcelero"], r["Color_Cinta"], int(r["Racimos"]), r["Estado"]
        ])
    ws.append_rows(filas)

def actualizar_fila_gsheet(num_fila_sheet, nueva_fila_lista):
    ws = conectar_hoja()
    rango = f"A{num_fila_sheet}:H{num_fila_sheet}"
    ws.update(values=[nueva_fila_lista], range_name=rango)

def borrar_fila_gsheet(num_fila_sheet):
    ws = conectar_hoja()
    ws.delete_rows(int(num_fila_sheet))

def procesar_csv_tableta(df_tab, col_lote, col_color, col_fecha=None):
    ahora = datetime.now()
    cols_usar = [col_lote, col_color]
    if col_fecha and col_fecha != "Usar fecha de hoy":
        cols_usar.append(col_fecha)
    df_limpio = df_tab[cols_usar].dropna().copy()
    if df_limpio.empty:
        return []
    if col_fecha and col_fecha != "Usar fecha de hoy":
        df_limpio["Fecha_Norm"] = pd.to_datetime(df_limpio[col_fecha], errors="coerce").dt.strftime("%Y-%m-%d")
        df_limpio["Fecha_Norm"] = df_limpio["Fecha_Norm"].fillna(ahora.strftime("%Y-%m-%d"))
    else:
        df_limpio["Fecha_Norm"] = ahora.strftime("%Y-%m-%d")
    conteo = df_limpio.groupby(["Fecha_Norm", col_lote, col_color]).size().reset_index(name="Total_Racimos")
    descuentos = []
    for _, fila in conteo.iterrows():
        lote_raw = str(fila[col_lote]).strip()
        num_lote = "".join(filter(str.isdigit, lote_raw))
        lote_norm = f"Lote {int(num_lote):02d}" if num_lote else lote_raw
        color_norm = str(fila[col_color]).strip().capitalize()
        cant = int(fila["Total_Racimos"])
        fecha_str = str(fila["Fecha_Norm"])
        try:
            semana_num = datetime.strptime(fecha_str, "%Y-%m-%d").isocalendar().week
        except Exception:
            semana_num = ahora.isocalendar().week
        descuentos.append({
            "Fecha": fecha_str,
            "Hora": ahora.strftime("%H:%M"),
            "Semana": semana_num,
            "Lote": lote_norm,
            "Parcelero": "Corte Tableta CSV",
            "Color_Cinta": color_norm,
            "Racimos": -cant,
            "Estado": "Cortado"
        })
    return descuentos

def mostrar_reportes_embolse(df, prefijo, lote_qr="Todos"):
    solo_emb = df[df["Racimos"] > 0].copy() if not df.empty else pd.DataFrame()
    if solo_emb.empty:
        st.info("Aún no hay registros de embolse en el sistema.")
        return
    ahora = datetime.now()
    solo_emb["Fecha"] = solo_emb["Fecha"].astype(str).str.strip().str[:10]
    solo_emb["Fecha_Dt"] = pd.to_datetime(solo_emb["Fecha"], errors="coerce").dt.date
    solo_emb["Anio"] = solo_emb["Fecha"].str[:4]
    solo_emb["Semana"] = solo_emb["Semana"].astype(int)

    fechas_validas = solo_emb["Fecha_Dt"].dropna()
    fecha_min = fechas_validas.min() if not fechas_validas.empty else ahora.date()
    fecha_max = fechas_validas.max() if not fechas_validas.empty else ahora.date()

    r1, r2 = st.columns(2)
    f_desde = r1.date_input("Desde fecha:", value=fecha_min, min_value=fecha_min, max_value=fecha_max, key=f"{prefijo}_desde")
    f_hasta = r2.date_input("Hasta fecha:", value=fecha_max, min_value=fecha_min, max_value=fecha_max, key=f"{prefijo}_hasta")

    f1, f2 = st.columns(2)
    sel_anio = f1.selectbox("Año:", ["Todos"] + sorted(solo_emb["Anio"].unique().tolist(), reverse=True), key=f"{prefijo}_anio")
    sel_sem = f2.selectbox("Semana Embolse:", ["Todas"] + sorted(solo_emb["Semana"].unique().tolist(), reverse=True), key=f"{prefijo}_sem")

    f3, f4, f5 = st.columns(3)
    lotes_op = ["Todos"] + sorted(solo_emb["Lote"].unique().tolist())
    idx_lote = lotes_op.index(lote_qr) if lote_qr in lotes_op else 0
    sel_lote = f3.selectbox("Lote:", lotes_op, index=idx_lote, key=f"{prefijo}_lote")
    sel_color = f4.selectbox("Color de Cinta:", ["Todos"] + sorted(solo_emb["Color_Cinta"].unique().tolist()), key=f"{prefijo}_color")
    sel_emp = f5.selectbox("Empleado:", ["Todos"] + sorted(solo_emb["Parcelero"].unique().tolist()), key=f"{prefijo}_emp")

    df_res = solo_emb[(solo_emb["Fecha_Dt"] >= f_desde) & (solo_emb["Fecha_Dt"] <= f_hasta)].copy()
    if sel_anio != "Todos":
        df_res = df_res[df_res["Anio"] == sel_anio]
    if sel_sem != "Todas":
        df_res = df_res[df_res["Semana"] == sel_sem]
    if sel_lote != "Todos":
        df_res = df_res[df_res["Lote"] == sel_lote]
    if sel_color != "Todos":
        df_res = df_res[df_res["Color_Cinta"] == sel_color]
    if sel_emp != "Todos":
        df_res = df_res[df_res["Parcelero"] == sel_emp]

    total_filtrado = int(df_res["Racimos"].sum())
    st.metric("Total General (Según Filtros)", f"{total_filtrado:,} racimos")

    st.write("### 1. Rendimiento por Lote (Racimos / Ha)")
    res_lote_ha = pd.DataFrame({"Lote": LOTES})
    res_lote_ha["Hectareas"] = res_lote_ha["Lote"].map(HECTAREAS_LOTE).fillna(0.0)
    emb_lote = df_res.groupby("Lote")["Racimos"].sum().reset_index()
    res_lote_ha = res_lote_ha.merge(emb_lote, on="Lote", how="left").fillna({"Racimos": 0})
    res_lote_ha["Racimos"] = res_lote_ha["Racimos"].astype(int)
    res_lote_ha["Racimos_Por_Ha"] = res_lote_ha.apply(lambda r: round(r["Racimos"] / r["Hectareas"], 1) if r["Hectareas"] > 0 else 0.0, axis=1)
    st.dataframe(
        res_lote_ha.style.background_gradient(subset=["Racimos_Por_Ha"], cmap="coolwarm_r").format({"Hectareas": "{:.2f}", "Racimos_Por_Ha": "{:.1f}"}),
        use_container_width=True, hide_index=True
    )

    st.write("### 2. Ranking de Empleados (Cantidad Total y Promedio por Día)")
    if not df_res.empty:
        rank_emp = df_res.groupby("Parcelero").agg(
            Total_Racimos=("Racimos", "sum"),
            Dias_Trabajados=("Fecha", "nunique")
        ).reset_index()
        rank_emp["Promedio_Por_Dia"] = (rank_emp["Total_Racimos"] / rank_emp["Dias_Trabajados"]).round(1)
        rank_emp = rank_emp.sort_values(by="Total_Racimos", ascending=False)
        st.dataframe(
            rank_emp.style.background_gradient(subset=["Total_Racimos", "Promedio_Por_Dia"], cmap="coolwarm_r").format({"Promedio_Por_Dia": "{:.1f}"}),
            use_container_width=True, hide_index=True
        )

    st.write("### 3. Embolse Consolidado por Día y Empleado")
    if not df_res.empty:
        por_dia = df_res.groupby(["Fecha", "Semana", "Parcelero"]).agg(
            Total_Dia=("Racimos", "sum"),
            Lotes=("Lote", lambda x: ", ".join(sorted(set(x)))),
            Cintas=("Color_Cinta", lambda x: ", ".join(sorted(set(x))))
        ).reset_index()
        por_dia = por_dia.sort_values(by="Total_Dia", ascending=False)
        st.dataframe(
            por_dia.style.background_gradient(subset=["Total_Dia"], cmap="coolwarm_r"),
            use_container_width=True, hide_index=True
        )

st.title("BANANERA LA LOLA S.A")

if len(st.session_state.cola_offline) > 0:
    st.warning(f"Tienes {len(st.session_state.cola_offline)} registro(s) guardados en el celular.")
    if st.button("Sincronizar ahora con Google Sheets", type="primary"):
        try:
            agregar_filas(st.session_state.cola_offline)
            st.session_state.cola_offline = []
            st.success("Registros sincronizados correctamente.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al sincronizar: {repr(e)}")

rol = st.radio("Selecciona perfil:", ["Parcelero (Embolse)", "Consulta de Embolse", "Administrador"], horizontal=True)

if rol == "Parcelero (Embolse)":
    st.subheader("Registro de Fruta Embolsada")
    lote_detectado = "Lote 01"
    if st.toggle("Activar cámara para escanear QR", key="qr_parcelero"):
        foto_qr = st.camera_input("Apunta al QR del Lote")
        if foto_qr:
            img_bgr = cv2.cvtColor(np.array(Image.open(foto_qr)), cv2.COLOR_RGB2BGR)
            dato_qr, _, _ = cv2.QRCodeDetector().detectAndDecode(img_bgr)
            if dato_qr in LOTES:
                lote_detectado = dato_qr
                st.success(f"Lote detectado: {lote_detectado}")
    opciones_lote = ["Selecciona Lote..."] + LOTES
    idx_lote_ini = opciones_lote.index(lote_detectado) if lote_detectado in opciones_lote else 0
    lote_sel = st.selectbox("Lote:", opciones_lote, index=idx_lote_ini, key="reg_lote")
    opciones_parc = ["Selecciona Parcelero..."] + PARCELEROS_BASE
    sel_p = st.selectbox("Parcelero / Responsable:", opciones_parc, key="reg_parcelero")
    if sel_p == "Otro (Escribir nombre)":
        parcelero = st.text_input("Nombre del trabajador:", key="reg_parc_otro").strip()
    else:
        parcelero = sel_p
    st.write("Toca el color de la cinta:")
    VISUAL_CINTAS = {
        "🟡 Amarilla": "Amarilla", "🟣 Morada": "Morada",
        "🔴 Roja": "Roja", "🟤 Café": "Café",
        "⚫ Negra": "Negra", "🟢 Verde": "Verde",
        "🔵 Azul": "Azul", "⚪ Blanca": "Blanca"
    }
    if "cinta_elegida" not in st.session_state:
        st.session_state.cinta_elegida = "Amarilla"
    cols_cinta = st.columns(4)
    for idx, (etiqueta, nombre_real) in enumerate(VISUAL_CINTAS.items()):
        with cols_cinta[idx % 4]:
            if st.button(etiqueta, key=f"cinta_{nombre_real}", use_container_width=True):
                st.session_state.cinta_elegida = nombre_real
    cinta = st.session_state.cinta_elegida
    st.info(f"Cinta seleccionada: **{cinta}**")
    col_fecha, col_cant, col_edad = st.columns(3)
    fecha_embolse = col_fecha.date_input("Fecha del embolse:", value=datetime.now(), key="reg_fecha")
    racimos = col_cant.number_input("Cantidad de racimos:", min_value=0, max_value=1000, value=0, key="reg_cant")
    edad_reg = col_edad.number_input("Edad al embolsar (sem):", min_value=0, max_value=15, value=1, key="reg_edad")
    if st.button("Guardar Embolse", type="primary"):
        if lote_sel == "Selecciona Lote..." or parcelero in ["Selecciona Parcelero...", ""] or racimos <= 0:
            st.warning("⚠️ Selecciona el Lote, el Parcelero y escribe una cantidad mayor a 0.")
        else:
            ahora = datetime.now()
            sem_embolse = fecha_embolse.isocalendar().week
            sem_real = sem_embolse - (int(edad_reg) - 1)
            if sem_real <= 0:
                sem_real += 52
            elif sem_real > 52:
                sem_real -= 52
            registro = {
                "Fecha": fecha_embolse.strftime("%Y-%m-%d"),
                "Hora": ahora.strftime("%H:%M"),
                "Semana": sem_real,
                "Lote": lote_sel,
                "Parcelero": parcelero,
                "Color_Cinta": cinta,
                "Racimos": int(racimos),
                "Estado": "En campo"
            }
            try:
                agregar_filas([registro])
                st.success(f"Guardados {racimos} racimos ({cinta}) en {lote_sel}.")
                time.sleep(1.5)
                for k in ["reg_lote", "reg_parcelero", "reg_parc_otro", "reg_cant"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()
            except Exception as e:
                st.error(f"Error técnico: {repr(e)}")



elif rol == "Consulta de Embolse":
    st.subheader("Consulta de Embolse (Puyas y Supervisores)")
    lote_qr = "Todos"
    if st.toggle("Activar cámara para escanear QR del Lote", key="qr_consulta"):
        foto_qr_p = st.camera_input("Apunta al QR del Lote")
        if foto_qr_p:
            img_bgr = cv2.cvtColor(np.array(Image.open(foto_qr_p)), cv2.COLOR_RGB2BGR)
            dato_qr, _, _ = cv2.QRCodeDetector().detectAndDecode(img_bgr)
            if dato_qr in LOTES:
                lote_qr = dato_qr
                st.success(f"Lote escaneado: {lote_qr}")
    df = cargar_datos()
    mostrar_reportes_embolse(df, prefijo="cons", lote_qr=lote_qr)

elif rol == "Administrador":
    clave = st.text_input("Clave de Administrador:", type="password")
    if clave != CLAVE_ADMIN:
        if clave != "":
            st.error("Clave incorrecta.")
        st.stop()
    tab1, tab2, tab3, tab4 = st.tabs(["Inventario y Edad", "Historial de Corte", "Subir CSV Tableta", "Corregir / Borrar"])
    df = cargar_datos()
    with tab1:
        st.subheader("Filtros y Rendimiento por Lote y Empleado")
        mostrar_reportes_embolse(df, prefijo="adm")
        st.divider()
        st.subheader("Proyección de Cosecha y Saldo en Mata (FIFO)")
        col_r1, col_r2 = st.columns(2)
        ratio = col_r1.number_input("Ratio (Cajas / Racimo):", value=1.15, min_value=0.50, max_value=2.50, step=0.05)
        merma = col_r2.slider("Merma estimada (%):", 0, 20, 5)
        if df.empty:
            st.warning("Aún no hay movimientos registrados.")
        else:
            ahora = datetime.now()
            semana_actual = ahora.isocalendar().week
            anio_actual = ahora.year
            df["Fecha"] = df["Fecha"].astype(str)
            df["Anio"] = df["Fecha"].str[:4]
            entradas = df[df["Racimos"] > 0].groupby(["Lote", "Color_Cinta", "Anio", "Semana"])["Racimos"].sum().reset_index()
            entradas = entradas.sort_values(by=["Lote", "Color_Cinta", "Anio", "Semana"])
            salidas = df[df["Racimos"] < 0].groupby(["Lote", "Color_Cinta"])["Racimos"].sum().abs().to_dict()
            filas_balance = []
            for _, fila in entradas.iterrows():
                lote = fila["Lote"]
                color = fila["Color_Cinta"]
                anio_str = str(fila["Anio"])
                sem = int(fila["Semana"])
                emb = int(fila["Racimos"])
                desc = min(emb, salidas.get((lote, color), 0))
                salidas[(lote, color)] = salidas.get((lote, color), 0) - desc
                saldo = emb - desc
                try:
                    y = int(anio_str)
                except Exception:
                    y = anio_actual
                edad = max(0, ((anio_actual - y) * 52 + (semana_actual - sem)) + 1)
                filas_balance.append({
                    "Lote": lote, "Color_Cinta": color, "Anio": anio_str,
                    "Semana_Emb": sem, "Edad": f"{edad} sem",
                    "Embolsados": emb, "Cortados": desc, "Saldo_En_Mata": saldo
                })
            balance = pd.DataFrame(filas_balance)
            if not balance.empty:
                solo_positivos = balance[balance["Saldo_En_Mata"] > 0]
                total_racimos = int(solo_positivos["Saldo_En_Mata"].sum())
                cajas_est = total_racimos * (1 - merma / 100.0) * ratio
                m1, m2 = st.columns(2)
                m1.metric("Saldo Real en Mata", f"{total_racimos:,} racimos")
                m2.metric("Cajas Proyectadas (20 kg)", f"{cajas_est:,.0f} cajas")
                st.write("Balance por Color y Edad (Toda la Finca)")
                bal_edad = balance.groupby(["Color_Cinta", "Anio", "Semana_Emb", "Edad"]).agg(
                    Embolsados=("Embolsados", "sum"), Cortados=("Cortados", "sum"), Saldo_En_Mata=("Saldo_En_Mata", "sum")
                ).reset_index()
                bal_edad["Cajas_Est"] = (bal_edad["Saldo_En_Mata"] * (1 - merma / 100.0) * ratio).round(0).astype(int)
                st.dataframe(bal_edad, use_container_width=True, hide_index=True)
                st.write("Balance Detallado por Lote y Edad (FIFO)")
                balance["Cajas_Est"] = (balance["Saldo_En_Mata"] * (1 - merma / 100.0) * ratio).round(0).astype(int)
                st.dataframe(balance, use_container_width=True, hide_index=True)


    with tab2:
        st.subheader("Buscador y Totales de Corte")
        solo_cortes = df[df["Racimos"] < 0].copy() if not df.empty else pd.DataFrame()
        if solo_cortes.empty:
            st.info("Aún no hay cortes registrados desde la tableta.")
        else:
            solo_cortes["Racimos_Cortados"] = solo_cortes["Racimos"].abs()
            solo_cortes["Fecha"] = solo_cortes["Fecha"].astype(str)
            solo_cortes["Anio"] = solo_cortes["Fecha"].str[:4]
            f1, f2, f3, f4 = st.columns(4)
            filtro_anio = f1.selectbox("Año:", ["Todos"] + sorted(solo_cortes["Anio"].unique().tolist(), reverse=True), key="corte_anio")
            filtro_fecha = f2.selectbox("Fecha:", ["Todas"] + sorted(solo_cortes["Fecha"].unique().tolist(), reverse=True), key="corte_fecha")
            filtro_lote = f3.selectbox("Lote:", ["Todos"] + sorted(solo_cortes["Lote"].unique().tolist()), key="corte_lote")
            filtro_color = f4.selectbox("Color:", ["Todos"] + sorted(solo_cortes["Color_Cinta"].unique().tolist()), key="corte_color")
            df_filtrado = solo_cortes.copy()
            if filtro_anio != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Anio"] == filtro_anio]
            if filtro_fecha != "Todas":
                df_filtrado = df_filtrado[df_filtrado["Fecha"] == filtro_fecha]
            if filtro_lote != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Lote"] == filtro_lote]
            if filtro_color != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Color_Cinta"] == filtro_color]
            total_cortados = int(df_filtrado["Racimos_Cortados"].sum())
            cajas_cortadas = total_cortados * ratio
            t1, t2 = st.columns(2)
            t1.metric("Total Racimos Cortados (Filtro)", f"{total_cortados:,} racimos")
            t2.metric("Cajas Equivalentes (Según Ratio)", f"{cajas_cortadas:,.0f} cajas")
            tabla_mostrar = df_filtrado[["Fecha", "Anio", "Semana", "Lote", "Color_Cinta", "Racimos_Cortados"]].sort_values(by="Fecha", ascending=False)
            st.dataframe(tabla_mostrar, use_container_width=True)
            csv_descarga = tabla_mostrar.to_csv(index=False).encode("utf-8")
            st.download_button("Descargar Selección en Excel (CSV)", data=csv_descarga, file_name="reporte_cortes_filtrado.csv", mime="text/csv")
  with tab3:
        st.subheader("Descontar Corte con CSV Directo de Tableta")
        st.write("Sube el archivo .csv de la tableta (cada fila cuenta como 1 racimo).")
        archivo_csv = st.file_uploader("Seleccionar archivo .csv de la tableta", type=["csv"])
        if archivo_csv is not None:
            try:
                df_tab = pd.read_csv(archivo_csv, sep=None, engine="python")
            except Exception:
                archivo_csv.seek(0)
                df_tab = pd.read_csv(archivo_csv)
            st.write("Vista previa del CSV cargado:")
            st.dataframe(df_tab.head(10), use_container_width=True)
            columnas_archivo = df_tab.columns.tolist()
            c1, c2, c3 = st.columns(3)
            col_lote = c1.selectbox("Columna de Lote:", columnas_archivo)
            col_color = c2.selectbox("Columna de Color:", columnas_archivo)
            col_fecha = c3.selectbox("Columna de Fecha:", ["Usar fecha de hoy"] + columnas_archivo)
            if st.button("Procesar CSV y Descontar Inventario", type="primary"):
                descuentos = procesar_csv_tableta(df_tab, col_lote, col_color, col_fecha)
                if descuentos:
                    try:
                        agregar_filas(descuentos)
                        total_desc = sum(abs(d["Racimos"]) for d in descuentos)
                        st.success(f"Listo. Se descontaron {total_desc} racimos respetando las fechas del CSV.")
                    except Exception as e:
                        st.error(f"Error técnico al descontar: {repr(e)}")
                else:
                    st.error("No se encontraron registros válidos en el CSV.")
with tab4:
        st.subheader("Corregir o Eliminar Registros (Solo Administrador)")
        if st.button("🔄 Recargar lista desde Google Sheets", key="btn_recargar_edit"):
            with st.spinner("Sincronizando con Google Sheets..."):
                time.sleep(1.5)
            st.rerun()
        if df.empty:
            st.warning("No se cargaron registros. Presiona el botón de recargar arriba.")
        else:
            df_edit = df.copy()
            df_edit["Fila_Excel"] = df_edit.index + 2
            df_edit["Tipo"] = df_edit["Racimos"].apply(lambda x: "Embolse (+)" if int(x) > 0 else "Corte (-)")
            c_f1, c_f2 = st.columns(2)
            f_lote_ed = c_f1.selectbox("Buscar por Lote:", ["Todos"] + sorted(df_edit["Lote"].astype(str).unique().tolist()), key="ed_filtro_lote")
            f_tipo_ed = c_f2.selectbox("Buscar por Tipo:", ["Todos", "Embolse (+)", "Corte (-)"], key="ed_filtro_tipo")
            df_filtrado_ed = df_edit.copy()
            if f_lote_ed != "Todos":
                df_filtrado_ed = df_filtrado_ed[df_filtrado_ed["Lote"] == f_lote_ed]
            if f_tipo_ed != "Todos":
                df_filtrado_ed = df_filtrado_ed[df_filtrado_ed["Tipo"] == f_tipo_ed]
            todos_ordenados = df_filtrado_ed.iloc[::-1]
            st.write(f"Mostrando **{len(todos_ordenados)}** registros encontrados:")
            st.dataframe(todos_ordenados[["Fila_Excel", "Fecha", "Semana", "Lote", "Parcelero", "Color_Cinta", "Racimos", "Estado"]], use_container_width=True, hide_index=True)
            if not todos_ordenados.empty:
                fila_sel = st.selectbox("Selecciona el número de Fila_Excel:", todos_ordenados["Fila_Excel"].tolist(), key="sel_fila_ed")
                datos_fila = df_edit[df_edit["Fila_Excel"] == fila_sel].iloc[int(0)]
                st.divider()
                st.write(f"Editando **Fila {fila_sel}** ({datos_fila['Parcelero']}):")
                parc_actual = str(datos_fila["Parcelero"])
                opciones_parc = PARCELEROS_BASE[:-1] + ["Otro / Manual"]
                idx_p = opciones_parc.index(parc_actual) if parc_actual in opciones_parc else len(opciones_parc) - 1
                sel_parc_ed = st.selectbox("Corregir Parcelero:", opciones_parc, index=idx_p, key=f"ed_parc_{fila_sel}")
                if sel_parc_ed == "Otro / Manual":
                    nuevo_parcelero = st.text_input("Nombre del trabajador:", value=parc_actual, key=f"ed_parc_txt_{fila_sel}").strip() or parc_actual
                else:
                    nuevo_parcelero = sel_parc_ed
                try:
                    fecha_obj = datetime.strptime(str(datos_fila["Fecha"]).strip()[:10], "%Y-%m-%d").date()
                except Exception:
                    fecha_obj = datetime.now().date()
                e1, e2 = st.columns(2)
                nueva_fecha = e1.date_input("Corregir Fecha:", value=fecha_obj, key=f"ed_fecha_{fila_sel}")
                idx_l = LOTES.index(datos_fila["Lote"]) if datos_fila["Lote"] in LOTES else 0
                nuevo_lote = e2.selectbox("Corregir Lote:", LOTES, index=idx_l, key=f"ed_lote_{fila_sel}")
                e3, e4 = st.columns(2)
                idx_c = COLORES_CINTA.index(datos_fila["Color_Cinta"]) if datos_fila["Color_Cinta"] in COLORES_CINTA else 0
                nuevo_color = e3.selectbox("Corregir Color:", COLORES_CINTA, index=idx_c, key=f"ed_color_{fila_sel}")
                valor_actual = int(float(datos_fila["Racimos"]))
                cant_real = abs(valor_actual) if abs(valor_actual) > 0 else 1
                nueva_cant_abs = e4.number_input("Corregir Cantidad:", min_value=1, max_value=10000, value=int(cant_real), key=f"ed_cant_{fila_sel}")
                nuevo_racimos = -int(nueva_cant_abs) if valor_actual < 0 else int(nueva_cant_abs)
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("💾 Guardar Corrección", type="primary", use_container_width=True, key=f"btn_save_{fila_sel}"):
                    try:
                        nueva_semana = nueva_fecha.isocalendar().week
                        fila_actualizada = [
                            nueva_fecha.strftime("%Y-%m-%d"), str(datos_fila["Hora"]), int(nueva_semana),
                            nuevo_lote, nuevo_parcelero, nuevo_color,
                            nuevo_racimos, str(datos_fila["Estado"])
                        ]
                        actualizar_fila_gsheet(int(fila_sel), fila_actualizada)
                        st.success(f"Fila {fila_sel} actualizada correctamente.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {repr(e)}")
                if col_btn2.button("🗑️ Eliminar Fila", use_container_width=True, key=f"btn_del_{fila_sel}"):
                    try:
                        borrar_fila_gsheet(int(fila_sel))
                        st.warning(f"Fila {fila_sel} eliminada permanentemente.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al eliminar: {repr(e)}")

