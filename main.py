import discord
from discord.ext import commands
from discord import app_commands
import json
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- CONFIGURACIÓN CON TUS CANALES ---
ID_CANAL_ASIGNACIONES = 1510702083379036210 # #asignaciones
ID_CANAL_ASCENSOS = 1510704139590697102 # #ascensos - aquí se anuncian los puntos
ID_CANAL_EVENTOS = 1510797476523802735 # #solicitar-eventos
ROLES_PERMITIDOS_ASIGNACION = ["Mayor", "Coronel", "Almirante"]
ARCHIVO_PUNTOS = "puntos.json"
# --- FIN DE CONFIGURACIÓN ---

def cargar_puntos():
    if not os.path.exists(ARCHIVO_PUNTOS):
        with open(ARCHIVO_PUNTOS, 'w') as f:
            json.dump({}, f)
    with open(ARCHIVO_PUNTOS, 'r') as f:
        return json.load(f)

def guardar_puntos(data):
    with open(ARCHIVO_PUNTOS, 'w') as f:
        json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Sincronizados {len(synced)} comandos')
    except Exception as e:
        print(e)

@bot.tree.command(name="asignacion", description="Crea una nueva asignación/evento oficial")
@app_commands.describe(
    nombre="Nombre de la operación",
    host="Quién organiza la operación",
    tiempo="Fecha y hora. Ej: 31/05 20:00 GMT-6",
    severidad="Nivel de amenaza de la operación",
    puntos="Puntos de ascenso que otorga",
    requerimientos="Qué se necesita para participar",
    duracion="Tiempo estimado de la operación",
    co_host="Co-anfitrión opcional"
)
@app_commands.choices(severidad=[
    app_commands.Choice(name="🟢 Verde - Riesgo Bajo", value="verde"),
    app_commands.Choice(name="🟡 Amarillo - Riesgo Medio", value="amarillo"),
    app_commands.Choice(name="🔴 Rojo - Riesgo Alto", value="rojo")
])
async def asignacion(
    interaction: discord.Interaction,
    nombre: str,
    host: str,
    tiempo: str,
    severidad: app_commands.Choice[str],
    puntos: int,
    requerimientos: str,
    duracion: str,
    co_host: str = "N/A"
):
    roles_user = [r.name for r in interaction.user.roles]
    if not any(rol in roles_user for rol in ROLES_PERMITIDOS_ASIGNACION):
        await interaction.response.send_message("No tienes autorización para crear asignaciones. Contacta a un Mayor o superior.", ephemeral=True)
        return

    colores = {"verde": "🟢", "amarillo": "🟡", "rojo": "🔴"}
    color_embed = discord.Color.green() if severidad.value == "verde" else discord.Color.yellow() if severidad.value == "amarillo" else discord.Color.red()

    embed = discord.Embed(
        title=f"🔱 | {nombre}",
        color=color_embed
    )

    embed.description = f"""
> **Anfitrión:** {host}
> **Co-Anfitrión:** {co_host}
>
> **Fecha y Hora:** {tiempo}
> **Severidad:** {colores[severidad.value]} {severidad.name.split('-')[1].strip()}
> **Puntos de Ascenso:** {puntos}
> **Requisitos:** {requerimientos}
> **Duración Estimada:** {duracion}
> **Notas:** Reacciona con ✅ para enlistarte a esta operación
"""
    embed.set_footer(text=f"Asignación publicada por {interaction.user.display_name}")
    embed.set_thumbnail(url="https://i.imgur.com/gJ3y4oJ.png") # Puedes cambiar esta imagen

    canal = bot.get_channel(ID_CANAL_ASIGNACIONES)
    if canal:
        msg = await canal.send(embed=embed)
        await msg.add_reaction("✅")
        await interaction.response.send_message(f"Asignación publicada correctamente en {canal.mention}", ephemeral=True)
    else:
        await interaction.response.send_message("Error: Canal de asignaciones no encontrado.", ephemeral=True)

@bot.tree.command(name="evento", description="Solicita un evento/operación al alto mando")
@app_commands.describe(
    nombre_solicitante="Tu nombre y rango actual",
    nombre_evento="Qué operación propones",
    tiempo_propuesto="Cuándo quieres realizarlo"
)
async def evento(interaction: discord.Interaction, nombre_solicitante: str, nombre_evento: str, tiempo_propuesto: str):
    canal = bot.get_channel(ID_CANAL_EVENTOS)
    if not canal:
        await interaction.response.send_message("Error: Canal de eventos no encontrado.", ephemeral=True)
        return

    embed = discord.Embed(
        title="📨 Nueva Solicitud de Operación",
        description=f"Solicitado por: {interaction.user.mention}",
        color=discord.Color.orange()
    )
    embed.add_field(name="Solicitante", value=nombre_solicitante, inline=True)
    embed.add_field(name="Operación Propuesta", value=nombre_evento, inline=False)
    embed.add_field(name="Fecha Propuesta", value=tiempo_propuesto, inline=True)
    embed.set_footer(text="El Alto Mando votará con 👍 para aprobar o 👎 para rechazar")

    msg = await canal.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

    await interaction.response.send_message("Tu solicitud fue enviada al Alto Mando. Espera la votación.", ephemeral=True)

@bot.tree.command(name="dar_puntos", description="Otorga puntos de ascenso a un miembro")
@app_commands.describe(miembro="A quién le das puntos", cantidad="Cuántos puntos otorgas", motivo="Razón del ascenso")
async def dar_puntos(interaction: discord.Interaction, miembro: discord.Member, cantidad: int, motivo: str):
    roles_user = [r.name for r in interaction.user.roles]
    if not any(rol in roles_user for rol in ROLES_PERMITIDOS_ASIGNACION):
        await interaction.response.send_message("No tienes autorización para dar puntos.", ephemeral=True)
        return

    puntos = cargar_puntos()
    user_id = str(miembro.id)

    if user_id not in puntos:
        puntos[user_id] = 0
    puntos[user_id] += cantidad
    guardar_puntos(puntos)

    # Anunciar en canal de ascensos
    canal_ascensos = bot.get_channel(ID_CANAL_ASCENSOS)
    if canal_ascensos:
        embed = discord.Embed(
            title="⭐ PUNTOS DE ASCENSO OTORGADOS ⭐",
            description=f"{miembro.mention} ha recibido **{cantidad} puntos**",
            color=discord.Color.gold()
        )
        embed.add_field(name="Motivo", value=motivo, inline=False)
        embed.add_field(name="Total Acumulado", value=f"{puntos[user_id]} puntos", inline=True)
        embed.add_field(name="Otorgado por", value=interaction.user.mention, inline=True)
        await canal_ascensos.send(embed=embed)

    await interaction.response.send_message(f"Se otorgaron **{cantidad} puntos** a {miembro.mention} por: {motivo}", ephemeral=True)

@bot.tree.command(name="puntos", description="Consulta los puntos de ascenso de un miembro")
@app_commands.describe(miembro="Deja vacío para ver tus propios puntos")
async def ver_puntos(interaction: discord.Interaction, miembro: discord.Member = None):
    target = miembro or interaction.user
    puntos = cargar_puntos()
    total = puntos.get(str(target.id), 0)
    
    embed = discord.Embed(
        title="📊 Registro de Puntos de Ascenso",
        description=f"{target.display_name} tiene **{total} puntos** acumulados.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

import os
bot.run(os.environ['TOKEN'])