import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Configuración de página para vista móvil
st.set_page_config(page_title="Control de Negocio", page_icon="📦", layout="centered")

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

# --- INTERFAZ DE USUARIO ---
st.title("📱 Control de Negocio")
menu = ["📊 Resumen", "📦 Inventario", "💳 Adeudos", "➕ Nuevo Registro"]
opcion = st.sidebar.selectbox("Menú Principal", menu)

# --- OPCCIÓN: RESUMEN ---
if opcion == "📊 Resumen":
    st.header("Resumen General")
    
    df_inv = pd.read_sql("SELECT * FROM inventario", conn)
    df_adeudos = pd.read_sql("SELECT * FROM adeudos WHERE estado = 'PENDIENTE'", conn)
    
    total_articulos = df_inv['stock'].sum() if not df_inv.empty else 0
    valor_inventario = (df_inv['stock'] * df_inv['precio_costo']).sum() if not df_inv.empty else 0
    total_adeudos = df_adeudos['saldo_pendiente'].sum() if not df_adeudos.empty else 0
    
    col1, col2 = st.columns(2)
    col1.metric("Unidades en Stock", f"{total_articulos} pcs")
    col2.metric("Valor Valorizado", f"${valor_inventario:,.2f}")
    
    st.metric("Total Cuentas por Cobrar", f"${total_adeudos:,.2f}", delta_color="inverse")

# --- OPCIÓN: INVENTARIO ---
elif opcion == "📦 Inventario":
    st.header("Inventario de Productos")
    
    df_inv = pd.read_sql("SELECT id, producto as 'Producto', stock as 'Stock', precio_costo as 'Costo ($)', precio_venta as 'Venta ($)' FROM inventario", conn)
    
    if not df_inv.empty:
        st.dataframe(df_inv, use_container_width=True)
    else:
        st.info("No hay productos registrados en el inventario.")

# --- OPCIÓN: ADEUDOS ---
elif opcion == "💳 Adeudos":
    st.header("Control de Adeudos")
    
    df_adeudos = pd.read_sql("SELECT id, cliente as 'Cliente', concepto as 'Concepto', saldo_pendiente as 'Saldo Pendiente ($)', fecha as 'Fecha' FROM adeudos WHERE estado = 'PENDIENTE'", conn)
    
    if not df_adeudos.empty:
        st.dataframe(df_adeudos, use_container_width=True)
        
        st.subheader("Registrar Abono")
        adeudo_sel = st.selectbox("Selecciona el Adeudo/Cliente", df_adeudos['id'].tolist(), format_func=lambda x: f"ID {x} - {df_adeudos[df_adeudos['id']==x]['Cliente'].values[0]} (${df_adeudos[df_adeudos['id']==x]['Saldo Pendiente ($)'].values[0]})")
        monto_abono = st.number_input("Monto del Abono ($)", min_value=1.0, step=10.0)
        
        if st.button("Registrar Pago/Abono"):
            saldo_act = df_adeudos[df_adeudos['id']==adeudo_sel]['Saldo Pendiente ($)'].values[0]
            nuevo_saldo = saldo_act - monto_abono
            nuevo_estado = "PAGADO" if nuevo_saldo <= 0 else "PENDIENTE"
            
            c.execute("UPDATE adeudos SET saldo_pendiente = ?, estado = ? WHERE id = ?", (max(0.0, nuevo_saldo), nuevo_estado, adeudo_sel))
            c.execute("INSERT INTO pagos (adeudo_id, monto_abono, fecha) VALUES (?, ?, ?)", (adeudo_sel, monto_abono, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            st.success("Abono registrado con éxito.")
            st.rerun()
    else:
        st.info("No hay adeudos pendientes registrados.")

# --- OPCIÓN: NUEVO REGISTRO ---
elif opcion == "➕ Nuevo Registro":
    st.header("Agregar Registros")
    tipo = st.radio("¿Qué deseas registrar?", ["Producto en Inventario", "Nuevo Adeudo / Crédito"])
    
    if tipo == "Producto en Inventario":
        with st.form("form_prod"):
            nombre = st.text_input("Nombre del Producto")
            stock = st.number_input("Cantidad / Stock Inicial", min_value=0, value=1)
            costo = st.number_input("Precio de Costo ($)", min_value=0.0, value=0.0)
            venta = st.number_input("Precio de Venta ($)", min_value=0.0, value=0.0)
            
            if st.form_submit_button("Guardar Producto"):
                if nombre:
                    c.execute("INSERT INTO inventario (producto, stock, precio_costo, precio_venta) VALUES (?, ?, ?, ?)", (nombre, stock, costo, venta))
                    conn.commit()
                    st.success(f"Producto '{nombre}' agregado exitosamente.")
                else:
                    st.error("Ingresa el nombre del producto.")
                    
    elif tipo == "Nuevo Adeudo / Crédito":
        with st.form("form_adeudo"):
            cliente = st.text_input("Nombre del Cliente")
            concepto = st.text_input("Concepto / Productos entregados")
            monto = st.number_input("Monto Total de Deuda ($)", min_value=1.0, value=100.0)
            
            if st.form_submit_button("Guardar Adeudo"):
                if cliente:
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M")
                    c.execute("INSERT INTO adeudos (cliente, concepto, monto_total, saldo_pendiente, fecha) VALUES (?, ?, ?, ?, ?)", (cliente, concepto, monto, monto, fecha_hoy))
                    conn.commit()
                    st.success(f"Adeudo registrado para {cliente}.")
                else:
                    st.error("Ingresa el nombre del cliente.")