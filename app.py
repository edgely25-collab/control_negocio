import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="BenyFerch - Control",
    page_icon="💎",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #d4af37; /* Color dorado acorde al logo */
        margin-bottom: 10px;
    }
    .metric-title { font-size: 14px; color: #6B7280; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 24px; font-weight: 700; color: #111827; }
    .stButton>button {
        width: 100%;
        background-color: #2c2c2c; /* Color oscuro elegante */
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 10px 16px;
    }
    .stButton>button:hover { background-color: #d4af37; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN A BASE DE DATOS Y MIGRACIÓN ---
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

def upgrade_db():
    try:
        c.execute("ALTER TABLE inventario ADD COLUMN stock_inicial INTEGER DEFAULT 0")
        c.execute("ALTER TABLE inventario ADD COLUMN entradas INTEGER DEFAULT 0")
        c.execute("ALTER TABLE inventario ADD COLUMN salidas INTEGER DEFAULT 0")
        c.execute("UPDATE inventario SET stock_inicial = stock WHERE stock_inicial = 0 AND entradas = 0 AND salidas = 0")
        conn.commit()
    except Exception:
        pass 

init_db()
upgrade_db()

# --- BARRA LATERAL CON LOGO Y NAVEGACIÓN ---
with st.sidebar:
    # Lógica inteligente para mostrar el logo si está en la carpeta
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    elif os.path.exists("logo.jpg"):
        st.image("logo.jpg", use_container_width=True)
    elif os.path.exists("logo.jpeg"):
        st.image("logo.jpeg", use_container_width=True)
    else:
        st.info("Sube tu logo.png a GitHub para verlo aquí")
        
    st.title("BenyFerch")
    st.caption("Joyería y Estampados - Control")
    st.divider()
    
    opciones_menu = ["📊 Resumen General", "📦 Inventario", "📥 Recepción de Inventario", "💳 Cuentas por Cobrar", "➕ Nuevo Registro", "✏️ Editar / Borrar"]
    opcion = st.radio("Navegación", opciones_menu)

# --- HEADER PRINCIPAL ---
st.title("📱 Panel de Control")

# --- OPCIÓN 1: RESUMEN GENERAL ---
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
            <div class="metric-title">Unidades en Stock Actual</div>
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

# --- OPCIÓN 2: INVENTARIO ---
elif opcion == "📦 Inventario":
    st.subheader("Catálogo de Productos")
    
    df_inv = pd.read_sql("SELECT id as 'ID', producto as 'Producto', precio_costo as 'Costo ($)', precio_venta as 'Venta ($)', stock_inicial as 'Inv. Inicial', entradas as 'Recepción (+)', salidas as 'Ventas (-)', stock as 'Inv. Final' FROM inventario", conn)
    
    if not df_inv.empty:
        st.dataframe(df_inv, use_container_width=True, hide_index=True)
    else:
        st.info("No hay productos registrados aún.")

# --- OPCIÓN 3: RECEPCIÓN DE INVENTARIO ---
elif opcion == "📥 Recepción de Inventario":
    st.subheader("Ingresar Mercancía (Resurtir)")
    
    df_inv = pd.read_sql("SELECT * FROM inventario", conn)
    if not df_inv.empty:
        prod_id = st.selectbox("Selecciona el Producto a Resurtir", df_inv['id'].tolist(), format_func=lambda x: f"ID {x} - {df_inv[df_inv['id']==x]['producto'].values[0]} (Stock actual: {df_inv[df_inv['id']==x]['stock'].values[0]})")
        
        with st.form("form_recepcion", clear_on_submit=True):
            cant_agregar = st.number_input("Cantidad a Ingresar", min_value=1, value=None, placeholder="Ej: 5")
            
            if st.form_submit_button("Guardar Entrada de Inventario"):
                if cant_agregar is not None:
                    c.execute("UPDATE inventario SET stock = stock + ?, entradas = entradas + ? WHERE id = ?", (cant_agregar, cant_agregar, prod_id))
                    conn.commit()
                    st.success("Inventario actualizado correctamente.")
                    st.rerun()
                else:
                    st.error("Ingresa una cantidad válida.")
    else:
        st.warning("Primero debes registrar un producto en 'Nuevo Registro'.")

# --- OPCIÓN 4: ADEUDOS Y ABONOS ---
elif opcion == "💳 Cuentas por Cobrar":
    st.subheader("Adeudos de Clientes")
    
    df_adeudos = pd.read_sql("SELECT id as 'ID', cliente as 'Cliente', concepto as 'Concepto', saldo_pendiente as 'Saldo Pendiente ($)', fecha as 'Fecha' FROM adeudos WHERE estado = 'PENDIENTE'", conn)
    
    if not df_adeudos.empty:
        st.dataframe(df_adeudos, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Registrar Abono")
        adeudo_sel = st.selectbox("Selecciona el Cliente / Folio", df_adeudos['ID'].tolist(), format_func=lambda x: f"ID {x} - {df_adeudos[df_adeudos['ID']==x]['Cliente'].values[0]} (${df_adeudos[df_adeudos['ID']==x]['Saldo Pendiente ($)'].values[0]})")
        
        with st.form("form_abono", clear_on_submit=True):
            monto_abono = st.number_input("Monto a Abonar ($)", min_value=0.1, value=None, placeholder="Ej: 50.0")
            
            if st.form_submit_button("Registrar Abono"):
                if monto_abono is not None:
                    saldo_act = df_adeudos[df_adeudos['ID']==adeudo_sel]['Saldo Pendiente ($)'].values[0]
                    nuevo_saldo = saldo_act - monto_abono
                    nuevo_estado = "PAGADO" if nuevo_saldo <= 0 else "PENDIENTE"
                    
                    c.execute("UPDATE adeudos SET saldo_pendiente = ?, estado = ? WHERE id = ?", (max(0.0, nuevo_saldo), nuevo_estado, adeudo_sel))
                    c.execute("INSERT INTO pagos (adeudo_id, monto_abono, fecha) VALUES (?, ?, ?)", (adeudo_sel, monto_abono, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success("Abono registrado correctamente.")
                    st.rerun()
                else:
                    st.error("Ingresa un monto válido.")
    else:
        st.success("🎉 ¡No hay cuentas pendientes por cobrar!")

# --- OPCIÓN 5: NUEVO REGISTRO ---
elif opcion == "➕ Nuevo Registro":
    st.subheader("Captura de Información")
    tipo = st.radio("Selecciona qué deseas registrar:", ["Producto Nuevo", "Nuevo Adeudo / Venta"], horizontal=True)
    
    if tipo == "Producto Nuevo":
        with st.form("form_prod", clear_on_submit=True):
            nombre = st.text_input("Nombre del Producto / Insumo")
            stock = st.number_input("Stock Inicial", min_value=0, value=None, placeholder="Ej: 10")
            costo = st.number_input("Precio de Costo ($)", min_value=0.0, value=None, placeholder="Ej: 50.0")
            venta = st.number_input("Precio de Venta ($)", min_value=0.0, value=None, placeholder="Ej: 150.0")
            
            if st.form_submit_button("Guardar Producto"):
                if nombre:
                    stock_v = stock if stock is not None else 0
                    costo_v = costo if costo is not None else 0.0
                    venta_v = venta if venta is not None else 0.0
                    
                    c.execute("INSERT INTO inventario (producto, stock, precio_costo, precio_venta, stock_inicial, entradas, salidas) VALUES (?, ?, ?, ?, ?, 0, 0)", (nombre, stock_v, costo_v, venta_v, stock_v))
                    conn.commit()
                    st.success(f"Producto '{nombre}' guardado exitosamente.")
                else:
                    st.error("Por favor ingresa el nombre del producto.")
                    
    elif tipo == "Nuevo Adeudo / Venta":
        df_inv = pd.read_sql("SELECT id, producto, stock, precio_venta FROM inventario WHERE stock > 0", conn)
        
        descontar_stock = st.checkbox("¿Descontar un producto del inventario?", value=False)
        prod_seleccionado_id = None
        cant_descontar = 1
        
        if descontar_stock:
            if not df_inv.empty:
                prod_opciones = {row['id']: f"{row['producto']} (Stock: {row['stock']} | Precio: ${row['precio_venta']})" for _, row in df_inv.iterrows()}
                prod_seleccionado_id = st.selectbox("Selecciona el Producto", list(prod_opciones.keys()), format_func=lambda x: prod_opciones[x])
                
                stock_max = int(df_inv[df_inv['id'] == prod_seleccionado_id]['stock'].values[0])
                precio_sugerido = float(df_inv[df_inv['id'] == prod_seleccionado_id]['precio_venta'].values[0])
                
                cant_descontar = st.number_input("Cantidad a entregar/vender", min_value=1, max_value=stock_max, value=1)
                monto_sugerido_total = precio_sugerido * cant_descontar
            else:
                st.warning("No hay productos con stock disponible para descontar.")
                descontar_stock = False
                monto_sugerido_total = 0.0
        else:
            monto_sugerido_total = 0.0

        with st.form("form_adeudo", clear_on_submit=True):
            cliente = st.text_input("Nombre del Cliente")
            
            if descontar_stock and prod_seleccionado_id:
                prod_nombre = df_inv[df_inv['id'] == prod_seleccionado_id]['producto'].values[0]
                concepto_inicial = f"{cant_descontar}x {prod_nombre}"
            else:
                concepto_inicial = ""
                
            concepto = st.text_input("Concepto / Detalles del trabajo", value=concepto_inicial)
            monto = st.number_input("Monto Total ($)", min_value=0.0, value=None, placeholder=f"Sugerido: ${monto_sugerido_total}")
            
            if st.form_submit_button("Guardar Deuda / Venta"):
                if cliente:
                    monto_v = monto if monto is not None else monto_sugerido_total
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M")
                    c.execute("INSERT INTO adeudos (cliente, concepto, monto_total, saldo_pendiente, fecha) VALUES (?, ?, ?, ?, ?)", (cliente, concepto, monto_v, monto_v, fecha_hoy))
                    
                    if descontar_stock and prod_seleccionado_id:
                        c.execute("UPDATE inventario SET stock = stock - ?, salidas = salidas + ? WHERE id = ?", (cant_descontar, cant_descontar, prod_seleccionado_id))
                        
                    conn.commit()
                    st.success(f"Registro exitoso para {cliente}.")
                else:
                    st.error("Por favor ingresa el nombre del cliente.")

# --- OPCIÓN 6: EDITAR Y ELIMINAR ---
elif opcion == "✏️ Editar / Borrar":
    st.subheader("Corrección de Registros")
    sub_opcion = st.radio("¿Qué deseas modificar?", ["Corregir Producto", "Corregir Adeudo"], horizontal=True)
    
    if sub_opcion == "Corregir Producto":
        df_inv = pd.read_sql("SELECT * FROM inventario", conn)
        if not df_inv.empty:
            prod_id = st.selectbox("Selecciona Producto a Corregir", df_inv['id'].tolist(), format_func=lambda x: f"ID {x} - {df_inv[df_inv['id']==x]['producto'].values[0]}")
            prod_row = df_inv[df_inv['id'] == prod_id].iloc[0]
            
            with st.form("edit_prod"):
                st.info("Solo edición de nombre y precios.")
                e_nombre = st.text_input("Nombre del Producto", value=prod_row['producto'])
                e_costo = st.number_input("Precio Costo ($)", min_value=0.0, value=float(prod_row['precio_costo']))
                e_venta = st.number_input("Precio Venta ($)", min_value=0.0, value=float(prod_row['precio_venta']))
                
                col_save, col_del = st.columns(2)
                if col_save.form_submit_button("Guardar Corrección"):
                    c.execute("UPDATE inventario SET producto=?, precio_costo=?, precio_venta=? WHERE id=?", (e_nombre, e_costo, e_venta, prod_id))
                    conn.commit()
                    st.success("Producto corregido correctamente.")
                    st.rerun()
                    
            if st.button("❌ Eliminar Producto Definitivamente"):
                c.execute("DELETE FROM inventario WHERE id=?", (prod_id,))
                conn.commit()
                st.warning("Producto eliminado.")
                st.rerun()
        else:
            st.info("No hay productos para editar.")

    elif sub_opcion == "Corregir Adeudo":
        df_adeudos = pd.read_sql("SELECT * FROM adeudos", conn)
        if not df_adeudos.empty:
            adeudo_id = st.selectbox("Selecciona Registro a Corregir", df_adeudos['id'].tolist(), format_func
