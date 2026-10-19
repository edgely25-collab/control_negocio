import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="BeniFerch - Control",
    page_icon="🎨",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    /* Color de fondo y tipografía */
    .main {
        background-color: #f8f9fa;
    }
    /* Estilo para las tarjetas de métricas */
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #4F46E5;
        margin-bottom: 10px;
    }
    .metric-title {
        font-size: 14px;
        color: #6B7280;
        font-weight: 600;
        text-transform: uppercase;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #111827;
    }
    /* Estilo del botón principal */
    .stButton>button {
        width: 100%;
        background-color: #4F46E5;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 10px 16px;
    }
    .stButton>button:hover {
        background-color: #4338CA;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN A BASE DE DATOS ---
conn = sqlite3.connect("negocio.db", check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS inventario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT NOT NULL,
                    stock INTEGER DEFAULT 0,
                    precio_costo REAL,
                    precio_venta REAL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS adeudos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente TEXT NOT NULL,
                    concepto TEXT,
                    monto_total REAL,
                    saldo_pendiente REAL,
                    fecha TEXT,
                    estado TEXT DEFAULT 'PENDIENTE'
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS pagos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    adeudo_id INTEGER,
                    monto_abono REAL,
                    fecha TEXT,
                    FOREIGN KEY(adeudo_id) REFERENCES adeudos(id)
                )''')
    conn.commit()

init_db()

# --- BARRA LATERAL CON LOGO Y NAVEGACIÓN ---
with st.sidebar:
    # Si tienes el link de una imagen o logo en la nube, puedes poner el URL aquí:
    st.image("https://img.icons8.com/color/96/design.png", width=70)
    st.title("BeniFerch")
    st.caption("Sistema de Gestión de Inventario y Adeudos")
    st.divider()
    
    opcion = st.radio("Navegación", ["📊 Resumen General", "📦 Inventario", "💳 Cuentas por Cobrar", "➕ Nuevo Registro"])

# --- HEADER PRINCIPAL ---
st.title("📱 Panel de Control")

# --- OPCCIÓN: RESUMEN GENERAL ---
if opcion == "📊 Resumen General":
    st.subheader("Estado Financiero y Stock")
    
    df_inv = pd.read_sql("SELECT * FROM inventario", conn)
    df_adeudos = pd.read_sql("SELECT * FROM adeudos WHERE estado = 'PENDIENTE'", conn)
    
    total_articulos = df_inv['stock'].sum() if not df_inv.empty else 0
    valor_inventario = (df_inv['stock'] * df_inv['precio_costo']).sum() if not df_inv.empty else 0
    total_adeudos = df_adeudos['saldo_pendiente'].sum() if not df_adeudos.empty else 0
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Unidades en Stock</div>
            <div class="metric-value">{total_articulos} pcs</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Valor en Inventario</div>
            <div class="metric-value">${valor_inventario:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #EF4444;">
        <div class="metric-title">Por Cobrar (Adeudos)</div>
        <div class="metric-value" style="color: #DC2626;">${total_adeudos:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# --- OPCIÓN: INVENTARIO ---
elif opcion == "📦 Inventario":
    st.subheader("Catálogo de Productos")
    
    df_inv = pd.read_sql("SELECT id as 'ID', producto as 'Producto', stock as 'Stock', precio_costo as 'Costo ($)', precio_venta as 'Venta ($)' FROM inventario", conn)
    
    if not df_inv.empty:
        st.dataframe(df_inv, use_container_width=True, hide_index=True)
    else:
        st.info("No hay productos registrados aún.")

# --- OPCIÓN: ADEUDOS ---
elif opcion == "💳 Cuentas por Cobrar":
    st.subheader("Adeudos de Clientes")
    
    df_adeudos = pd.read_sql("SELECT id as 'ID', cliente as 'Cliente', concepto as 'Concepto', saldo_pendiente as 'Saldo Pendiente ($)', fecha as 'Fecha' FROM adeudos WHERE estado = 'PENDIENTE'", conn)
    
    if not df_adeudos.empty:
        st.dataframe(df_adeudos, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Registrar Abono")
        adeudo_sel = st.selectbox("Selecciona el Cliente / Folio", df_adeudos['ID'].tolist(), format_func=lambda x: f"ID {x} - {df_adeudos[df_adeudos['ID']==x]['Cliente'].values[0]} (${df_adeudos[df_adeudos['ID']==x]['Saldo Pendiente ($)'].values[0]})")
        monto_abono = st.number_input("Monto a Abonar ($)", min_value=1.0, step=10.0)
        
        if st.button("Registrar Abono"):
            saldo_act = df_adeudos[df_adeudos['ID']==adeudo_sel]['Saldo Pendiente ($)'].values[0]
            nuevo_saldo = saldo_act - monto_abono
            nuevo_estado = "PAGADO" if nuevo_saldo <= 0 else "PENDIENTE"
            
            c.execute("UPDATE adeudos SET saldo_pendiente = ?, estado = ? WHERE id = ?", (max(0.0, nuevo_saldo), nuevo_estado, adeudo_sel))
            c.execute("INSERT INTO pagos (adeudo_id, monto_abono, fecha) VALUES (?, ?, ?)", (adeudo_sel, monto_abono, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            st.success("Abono registrado correctamente.")
            st.rerun()
    else:
        st.success("🎉 ¡No hay cuentas pendientes por cobrar!")

# --- OPCIÓN: NUEVO REGISTRO ---
elif opcion == "➕ Nuevo Registro":
    st.subheader("Captura de Información")
    tipo = st.segmented_control("Selecciona el tipo de captura:", ["Producto", "Adeudo / Crédito"], default="Producto")
    
    if tipo == "Producto":
        with st.form("form_prod"):
            nombre = st.text_input("Nombre del Producto / Insumo")
            stock = st.number_input("Stock Inicial", min_value=0, value=1)
            costo = st.number_input("Precio de Costo ($)", min_value=0.0, value=0.0)
            venta = st.number_input("Precio de Venta ($)", min_value=0.0, value=0.0)
            
            if st.form_submit_button("Guardar Producto"):
                if nombre:
                    c.execute("INSERT INTO inventario (producto, stock, precio_costo, precio_venta) VALUES (?, ?, ?, ?)", (nombre, stock, costo, venta))
                    conn.commit()
                    st.success(f"Producto '{nombre}' guardado exitosamente.")
                else:
                    st.error("Por favor ingresa el nombre del producto.")
                    
    elif tipo == "Adeudo / Crédito":
        with st.form("form_adeudo"):
            cliente = st.text_input("Nombre del Cliente")
            concepto = st.text_input("Concepto / Detalles del trabajo")
            monto = st.number_input("Monto Total ($)", min_value=1.0, value=100.0)
            
            if st.form_submit_button("Guardar Adeudo"):
                if cliente:
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M")
                    c.execute("INSERT INTO adeudos (cliente, concepto, monto_total, saldo_pendiente, fecha) VALUES (?, ?, ?, ?, ?)", (cliente, concepto, monto, monto, fecha_hoy))
                    conn.commit()
                    st.success(f"Adeudo registrado a nombre de {cliente}.")
                else:
                    st.error("Por favor ingresa el nombre del cliente.")
