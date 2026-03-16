import random
import json
import os
import sys
import time
from collections import defaultdict

# ANSI colores y estilos para consola
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

# Texto lento para ambientación
def escribir_lento(texto, velocidad=0.03):
    for letra in texto:
        sys.stdout.write(letra)
        sys.stdout.flush()
        time.sleep(velocidad)
    print()

# Validación segura para inputs numéricos

def input_seguro(prompt, min_op=1, max_op=99):
    while True:
        try:
            valor = int(input(prompt))
            if min_op <= valor <= max_op:
                return valor
            else:
                print(f"{RED}⛔ Opción fuera de rango.{RESET}")
        except ValueError:
            print(f"{RED}⛔ Entrada inválida. Por favor, ingresa un número.{RESET}")

# Separador visual

def separador():
    print(f"{BOLD}{CYAN}" + "═" * 50 + f"{RESET}")

class Objeto:
    def __init__(self, nombre, tipo, efecto=None, ataque=0, defensa=0, descripcion=""):
        self.nombre = nombre
        self.tipo = tipo
        self.efecto = efecto
        self.ataque = ataque
        self.defensa = defensa
        self.descripcion = descripcion  # Agregamos una descripción opcional al objeto

    def __str__(self):
        return self.nombre

class Personaje:
    def __init__(self, nombre, vida, ataque, nivel=1, es_enemigo=False):
        self.nombre = nombre
        self.nivel = nivel
        self.vida_max = vida + (nivel - 1) * 5 if es_enemigo else vida
        self.vida = self.vida_max
        self.ataque = ataque + (nivel - 1) * 2 if es_enemigo else ataque
        self.magia = 5
        self.magia_max = 5 + (nivel // 2)
        self.defensa_fisica = 3 + (nivel - 1) if es_enemigo else 3
        self.defensa_magica = 3 + (nivel - 1) if es_enemigo else 3
        self.agilidad = 5 + (nivel - 1) if es_enemigo else 5
        self.velocidad = 55 + (nivel - 1) if es_enemigo else 5
        self.exp = 0
        self.inventario = defaultdict(list)
        self.arma = None
        self.armadura = None
        self.companeros = []
        self.companero_activo = None
        self.bestiario = set()  # Conjunto de nombres de enemigos enfrentados


        if not es_enemigo:
            self.inventario['utiles'].append(Objeto("Tortilla de rescoldo", "utiles", lambda p: self.curacion(p, 15)))

    def curacion(self, personaje, cantidad):
        personaje.vida = min(personaje.vida + cantidad, personaje.vida_max)
        print(f"y ha recuperado {GREEN}{cantidad}{RESET} de salud!")

    def uso_magia(self, enemigo):
        costo = 2  # Costo de magia por hechizo
        if self.magia < costo:
            print(f"{self.nombre} no tiene suficiente magia para lanzar el hechizo.")
            return

        self.magia -= costo  # Se descuenta magia

        if random.randint(1, 100) <= enemigo.agilidad * 1.5:
            print(f"{enemigo.nombre} esquiva el hechizo de {self.nombre}!")
            return

        danio = self.magia_max * 2 - enemigo.defensa_magica  # Se usa magia_max para mantener el daño constante
        danio = max(danio, 1)
        enemigo.vida -= danio
        print(f"{self.nombre} lanza un hechizo a {enemigo.nombre} y causa {danio} de daño mágico.")


    def atacar(self, enemigo):
        if random.randint(1, 100) <= enemigo.agilidad * 2:
            print(f"{enemigo.nombre} esquiva el ataque de {self.nombre}!")
            return

        # Ajuste del cálculo de daño para mejor escala
        danio_base = (self.ataque_total() ** 1.1) / (enemigo.defensa_fisica_total() + 1)
        danio_base += 2  # daño mínimo base para no hacer solo 1

        danio_min = max(1, int(danio_base * 0.8))
        danio_max = max(danio_min, int(danio_base * 1.2))
        danio = random.randint(danio_min, danio_max)

        critico = random.random() < 0.05
        if critico:
            danio = int(danio * 1.75)

        danio = max(int(danio), 1)
        enemigo.vida -= danio

        mensaje = f"{self.nombre} ataca a {enemigo.nombre} y causa {BOLD}{RED}-{danio}{RESET} de daño."
        if critico:
            mensaje += f" {BOLD}{YELLOW}¡Golpe crítico!{RESET}"
        elif danio >= 10:
            mensaje += f" {RED}{BOLD}(¡Un golpe devastador!){RESET}"

        print(mensaje)

    def ataque_total(self):
        base = self.ataque + self.nivel
        if self.arma:
            base += self.arma.ataque
        return base

    def defensa_fisica_total(self):
        base = self.defensa_fisica + self.nivel
        if self.armadura:
            base += self.armadura.defensa
        return base

    def esta_vivo(self):
        return self.vida > 0

    def usar_objeto(self, durante_combate=False, enemigo=None):
        if not self.inventario['utiles']:
            print("No tienes objetos para usar.")
            return
        
        print("Selecciona un objeto para usar:")
        for i, obj in enumerate(self.inventario['utiles']):
            print(f"{i + 1}. {obj.nombre}")
        
        print("0. 🔙 Cancelar")

        try:
            eleccion = int(input("> ")) - 1
            if eleccion == -1:
                print("❌ Cancelado.")
                return

            # Asegurarse de que la elección esté en el rango correcto
            if 0 <= eleccion < len(self.inventario['utiles']):
                objeto = self.inventario['utiles'][eleccion]

                # Mostrar descripción si existe
                print(f"\n🔍 {objeto.nombre}")
                if hasattr(objeto, 'descripcion'):
                    print(f"📝 {objeto.descripcion}")

                # Confirmar si el jugador quiere usar el objeto
                confirmar = input("\n¿Quieres usar este objeto? (s/n): ").lower()
                if confirmar != 's':
                    print("❌ No se usó el objeto.")
                    return

                # Aplicar el efecto y eliminar del inventario
                print(f"\n✅El Jugador ha usado {objeto.nombre}...")
                if durante_combate:
                    objeto.efecto(self)  # Ejecutar efecto en combate
                else:
                    objeto.efecto(self)  # Ejecutar efecto fuera de combate

                # Eliminar el objeto del inventario solo una vez
                self.inventario['utiles'].pop(eleccion)
            else:
                print("⚠️ Selección fuera de rango.")
        except (ValueError, IndexError):
            print("❌ Entrada inválida. Intenta con un número.")



    def ganar_exp(self, cantidad):
        self.exp += cantidad
        print(f"{self.nombre} gana {GREEN}{BOLD}{cantidad}{RESET} puntos de experiencia.")
        if self.exp >= 10 * self.nivel:
            self.nivel += 1
            self.vida_max += 10
            self.vida = self.vida_max
            self.ataque += 2
            self.magia_max += 1
            self.magia = self.magia_max
            self.defensa_fisica += 1
            self.defensa_magica += 1
            self.agilidad += 1
            self.velocidad += 1
            print(f"¡{self.nombre} ha subido a nivel {self.nivel}!")
            historia_nivel(self.nivel)
            if self.nivel == 3:
                self.reclutar_companero("Lizama, el Barbon")

    def mostrar_estadisticas(self):
        print(f"""
    ╔══════════ {BOLD}{BLUE}📊 ESTADÍSTICAS{RESET} ═════════╗
    ║ Nombre: {CYAN}{self.nombre}{RESET}
    ║ Nivel: {YELLOW}{self.nivel}{RESET} | EXP: {self.exp}/{self.nivel * 10}
    ║ ❤️  Salud: {GREEN}{self.vida}/{self.vida_max}{RESET}    
    ║ ⚔️  Ataque: {self.ataque_total():<6} 🔮 Magia: {MAGENTA}{self.magia}/{self.magia_max}{RESET}      
    ║ 🧠 Def. Mágica: {self.defensa_magica:<1} 🛡️  Def. Física: {self.defensa_fisica_total()}
    ║ 💨 Agilidad: {self.agilidad:<5} ⚡Velocidad: {self.velocidad}
    ╚════════════════════════════════════╝{RESET}""")

    def mostrar_inventario(self):
        while True:
            limpiar_pantalla()  # 🔄 Limpiamos pantalla antes de mostrar todo
            separador()
            self.mostrar_estadisticas()

            print(f"\n{BOLD}{MAGENTA}🎒 INVENTARIO{RESET}")
            for tipo, lista in self.inventario.items():
                print(f"{MAGENTA} {tipo.capitalize():<10} ({len(lista)}):{RESET}")
                for i, item in enumerate(lista):
                    print(f"  {i + 1}. {item.nombre}")
            print(f"{MAGENTA}\nArma equipada: {self.arma.nombre if self.arma else 'Ninguna'}")
            print(f"Armadura equipada: {self.armadura.nombre if self.armadura else 'Ninguna'}\n")
            separador()
            print(f"""{BOLD}{CYAN}🚩¿Qué quieres hacer?
        1. 🧪 Usar objeto       
        2. ⚔️  Equipar arma      
        3. 🛡️  Equipar armadura  
        4. 📊 Ver estadísticas  
        5. 🔙 Volver{RESET}""")
            separador()
            subop = input("> ")

            if subop == "1":
                self.usar_objeto()
                input(f"{GREEN}✅ Objeto usado. Presiona Enter para continuar...{RESET}")
            elif subop == "2":
                self.equipar("arma")
                input(f"{GREEN}✅ Arma equipada. Presiona Enter para continuar...{RESET}")
            elif subop == "3":
                self.equipar("armadura")
                input(f"{GREEN}✅ Armadura equipada. Presiona Enter para continuar...{RESET}")
            elif subop == "4":
                self.mostrar_estadisticas()
                input(f"{CYAN}📊 Fin de estadísticas. Presiona Enter para volver al inventario...{RESET}")
            elif subop == "5":
                limpiar_pantalla()
                break
            else:
                print(f"{RED}❌ Opción no válida. Intenta de nuevo.{RESET}")
                input("Presiona Enter para continuar...")


    def equipar(self, tipo):
        opciones = self.inventario.get(tipo + 's', [])
        
        if not opciones:
            print(f"No tienes {tipo}s para equipar.")
            return
        
        while True:
            print(f"\n🔧 Elige un(a) {tipo} para equipar:")
            for i, item in enumerate(opciones):
                print(f"{i + 1}. {item.nombre}")
            print("0. 🔙 Cancelar")
            
            try:
                eleccion = int(input("> ")) - 1
                if eleccion == -1:
                    print("❌ Cancelado.")
                    return
                
                if 0 <= eleccion < len(opciones):
                    item_nuevo = opciones.pop(eleccion)
                    
                    # Mostrar detalles si existen
                    print(f"\n🛠️ {item_nuevo.nombre}")
                    if hasattr(item_nuevo, 'descripcion'):
                        print(f"📝 {item_nuevo.descripcion}")
                    if hasattr(item_nuevo, 'bono_ataque'):
                        print(f"⚔️ Bono de ataque: {item_nuevo.bono_ataque}")
                    if hasattr(item_nuevo, 'bono_defensa'):
                        print(f"🛡️ Bono de defensa: {item_nuevo.bono_defensa}")
                    
                    # Confirmación
                    confirmar = input("\n¿Quieres equiparlo? (s/n): ").lower()
                    if confirmar != 's':
                        print("❌ No se equipó.")
                        continue
                    
                    # Si ya hay uno equipado, lo devolvemos al inventario
                    if tipo == "arma":
                        if self.arma:
                            self.inventario["armas"].append(self.arma)
                        self.arma = item_nuevo
                    elif tipo == "armadura":
                        if self.armadura:
                            self.inventario["armaduras"].append(self.armadura)
                        self.armadura = item_nuevo
                    
                    print(f"✅ Has equipado {item_nuevo.nombre}.")
                    break
                else:
                    print("⚠️ Selección fuera de rango.")
            
            except (ValueError, IndexError):
                print("❌ Entrada inválida. Intenta con un número.")


    def reclutar_companero(self, nombre):
        print(f"¡{nombre} se ha unido a tu grupo!")
        nuevo_companero = Personaje(nombre, 20, 5)  # Puedes ajustar stats
        self.companeros.append(nuevo_companero)
        self.companero_activo = nuevo_companero

    def guardar(self):
        inventario_serializado = {
            tipo: [obj.nombre for obj in lista]
            for tipo, lista in self.inventario.items()
        }

        # Guardar el objeto del personaje
        with open(f"{self.nombre}_save.json", "w") as f:
            datos = {
                'nombre': self.nombre,
                'vida': self.vida,
                'vida_max': self.vida_max,
                'ataque': self.ataque,
                'magia': self.magia,
                'defensa_fisica': self.defensa_fisica,
                'defensa_magica': self.defensa_magica,
                'agilidad': self.agilidad,
                'velocidad': self.velocidad,
                'nivel': self.nivel,
                'exp': self.exp,
                'arma': self.arma.nombre if self.arma else None,
                'armadura': self.armadura.nombre if self.armadura else None,
                'companeros': [comp.nombre for comp in self.companeros],
                'inventario': inventario_serializado
            }
            json.dump(datos, f, indent=4)

    @staticmethod
    def cargar(nombre):
        if os.path.exists(f"{nombre}_save.json"):
            with open(f"{nombre}_save.json", "r") as f:
                datos = json.load(f)

                # Crear el personaje base con las estadísticas guardadas
                personaje = Personaje(datos['nombre'], datos['vida_max'], datos['ataque'])
                personaje.__dict__.update({k: v for k, v in datos.items() if k != 'inventario' and k != 'companeros'})

                # Restaurar inventario
                inventario = defaultdict(list)
                for tipo, objetos in datos['inventario'].items():
                    for nombre in objetos:
                        if nombre == "Tortilla de rescoldo":
                            inventario[tipo].append(Objeto(nombre, tipo, lambda p: personaje.curacion(p, 15)))
                        elif nombre == "Pan con Chicharrones":
                            inventario[tipo].append(Objeto(nombre, tipo, lambda p: personaje.curacion(p, 30)))
                        else:
                            inventario[tipo].append(Objeto(nombre, tipo))
                personaje.inventario = inventario

                # Restaurar compañeros
                for comp_nombre in datos['companeros']:
                    nuevo_companero = Personaje(comp_nombre, 20, 5)  # Asegúrate de ajustar las stats si es necesario
                    personaje.companeros.append(nuevo_companero)

                # Equipar el arma y armadura si se tenían
                if datos['arma']:
                    personaje.arma = Objeto(datos['arma'], "armas")
                if datos['armadura']:
                    personaje.armadura = Objeto(datos['armadura'], "armaduras")

                return personaje
        return None

    @staticmethod
    def from_dict(data):
        # Reasocia efecto según el nombre
        if data['nombre'] == "Tortilla de rescoldo":
            efecto = lambda p: p.curacion(p, 15)
        elif data['nombre'] == "Poción mágica":
            efecto = lambda p: p.uso_magia(p)
        else:
            efecto = None
        return Objeto(data['nombre'], data['tipo'], efecto)


def historia_inicio():
    print()
    escribir_lento("    Bajo las tierras negras de Lota, donde el carbón susurra secretos antiguos,", 0.04)
    time.sleep(0.5)
    escribir_lento("    los viejos mineros hablaban de un túnel maldito: El Chiflón del Diablo.", 0.04)
    time.sleep(0.5)
    escribir_lento("    Allí, decían, no solo se extraía carbón, sino también almas.", 0.04)
    time.sleep(1)
    escribir_lento("    Durante décadas, familias enteras vivieron a la sombra de esa boca infernal,", 0.04)
    escribir_lento("    hasta que un derrumbe selló el acceso... o eso creyeron todos.", 0.04)
    time.sleep(1)
    escribir_lento("\n    Hoy, tú desciendes a ese abismo.", 0.04)
    escribir_lento("    No por gloria ni por oro...", 0.04)
    escribir_lento("    sino para descubrir qué fue de los que nunca salieron...", 0.04)
    escribir_lento("    y enfrentar al verdadero dueño de las profundidades:\n", 0.04)
    escribir_lento("    El diente de ORO...\n", 0.04)
    time.sleep(1)  
    escribir_lento(f"    Mejor conocido como: {RED}El Diablo...{RED}{RESET}.\n", 0.04)
    time.sleep(2)

def historia_nivel(nivel):
    historias = {
        2: "Mientras avanzas, ves cascos oxidados y herramientas olvidadas. Aquí hubo vida... y muerte.",
        3: "Un mural tallado en la roca muestra una figura con cuernos y carbón por piel. ¿Una advertencia?",
        4: "Oyes una voz... no en tu oído, sino en tu cabeza. Susurra nombres de mineros caídos.",
        5: "Encuentras un viejo libro quemado con el título apenas visible: 'Contrato con el Carbón'.",
        6: "Una lámpara se enciende sola. A su luz, ves sombras de obreros que ya no están vivos... pero tampoco muertos."
    }
    if nivel in historias:
        print(f"\n--- Historia del nivel {nivel} ---\n{historias[nivel]}\n")

def mostrar_estado(jugador, enemigo):
    # Salud en rojo si es menor al 20%
    porcentaje_salud = jugador.vida / jugador.vida_max
    salud_color = RED if porcentaje_salud <= 0.2 else RESET

    # Magia en rojo si es 1 o 0
    salud_magia = RED if jugador.magia <= 1 else RESET
    print(f"""
╔═════════════ {BOLD}{RED}⚔️ ESTADO DE COMBATE{RESET} ═════════════╗
║🧍 {jugador.nombre} - Nivel {jugador.nivel}
║   ❤️  Salud: {salud_color}{BOLD}{jugador.vida}{RESET}/{jugador.vida_max}
║   ⚔️  Ataque: {jugador.ataque_total():<6} | 🔮 Magia: {salud_magia}{BOLD}{jugador.magia}{RESET}/{jugador.magia_max}
║   🛡️  Def. Física: {jugador.defensa_fisica_total():<1} | 🛡️  Def. Mágica: {jugador.defensa_magica}
║   💨 Agilidad: {jugador.agilidad:<4} | ⚡ Velocidad: {jugador.velocidad}
╠══════════════════════════════════════════════╣
║👹 Enemigo: {enemigo.nombre}
║   💀 Nivel: {enemigo.nivel:<3}     ❤️ Salud: {enemigo.vida}
╚══════════════════════════════════════════════╝
""")

def explorar_mazmorra(jugador):
    # Se elige un evento aleatorio
    evento = random.choices(
        ["enemigo", "nada", "tesoro", "trampa", "npc", "puerta_cerrada"],
        weights=[40, 30, 15, 10, 5, 5],  # Probabilidades generales
        k=1
    )[0]

    if evento == "enemigo":
        nivel_enemigo = random.randint(jugador.nivel, jugador.nivel + 2)
        enemigos = [
            Personaje("La Viuda del Carbón", 15, 5, nivel=nivel_enemigo, es_enemigo=True),
            Personaje("Capataz Zaldívar", 12, 4, nivel=nivel_enemigo, es_enemigo=True),
            Personaje("El Encapuchado de Humo", 20, 6, nivel=nivel_enemigo, es_enemigo=True),
            Personaje("El Roto del Derrumbe", 18, 6, nivel=nivel_enemigo, es_enemigo=True),
            Personaje("Niño de la Linterna", 12, 4, nivel=nivel_enemigo, es_enemigo=True),
            Personaje("Fantasma del Chiflón", 20, 7, nivel=nivel_enemigo, es_enemigo=True),
            Personaje("Perro del Tajo 7", 14, 5, nivel=nivel_enemigo, es_enemigo=True),
            Personaje("El Gritón de la Veta", 22, 8, nivel=nivel_enemigo, es_enemigo=True),
        ]
        enemigo = random.choice(enemigos)
        
        descripciones_enemigos = {
            "La Viuda del Carbón": "Una figura fantasmal vestida de luto, cuyo llanto ahoga el eco del túnel.",
            "Capataz Zaldívar": "Aún con su casco y látigo, su alma dirige los turnos de los muertos.",
            "El Encapuchado de Humo": "Donde camina, el aire se vuelve espeso y sulfuroso.",
            "El Roto del Derrumbe": "Cubierto de polvo y piedras, se arrastra buscando su pierna perdida.",
            "Niño de la Linterna": "Una linterna parpadea sola en la oscuridad... pero no hay mano que la sujete.",
            "Fantasma del Chiflón": "Los vientos traen su silueta, envuelta en murmullos y quejidos.",
            "Perro del Tajo 7": "Sus ojos brillan como brasas, su cuerpo hecho de sombras mineras.",
            "El Gritón de la Veta": "Grita nombres de obreros desaparecidos... y a veces el tuyo.",
            }
        descripcion = descripciones_enemigos.get(enemigo.nombre, "")
        
        if descripcion:
            escribir_lento(f"{YELLOW}{descripcion}{RESET}", 0.03)
   
        combate_por_turnos(jugador, enemigo)

    elif evento == "nada":
        print(f"{YELLOW}🌫️ No encuentras nada útil aquí.{RESET}")

    elif evento == "tesoro":
        tipos_tesoro = ["utiles", "armas", "armaduras"]
        tipo_elegido = random.choices(tipos_tesoro, weights=[50, 30, 20], k=1)[0]

        tesoros_por_tipo = {
            "utiles": [
                Objeto("Tortilla de rescoldo", 
                        "utiles", 
                        lambda p: p.curacion(p, 15), 
                        descripcion="Un clásico del minero, calienta el alma y cura 15 de salud."),
                Objeto("Pan con Chicharrones", 
                        "utiles", 
                        lambda p: p.curacion(p, 30), 
                        descripcion="Delicioso pan contundente, restaura 30 de salud y motivación."),
            ],
            "armas": [
                Objeto("Pico oxidado", "armas", ataque=3),
                Objeto("Hacha de minero", "armas", ataque=5),
            ],
            "armaduras": [
                Objeto("Casco de minero", "armaduras", defensa=2),
                Objeto("Chaleco reforzado", "armaduras", defensa=4),
            ]
        }

        tesoro = random.choice(tesoros_por_tipo[tipo_elegido])
        jugador.inventario[tesoro.tipo].append(tesoro)
        print(f"\u00a1Has encontrado un {tesoro.nombre}!")

    elif evento == "trampa":
        # El jugador tiene que decidir si evita la trampa
        print("¡Cuidado! Has encontrado una trampa.")
        if random.random() < 0.5:  # 50% de probabilidades de ser evitada
            print("¡La trampa es desactivada a tiempo!")
        else:
            dano_trampa = random.randint(5, 15)
            jugador.vida -= dano_trampa
            print(f"¡Oh no! La trampa te ha causado {dano_trampa} puntos de daño.")

    elif evento == "npc":
        npc = random.choice(["El Sabio de las Sombras", "Mercader del abismo", "Luchador errante"])
        print(f"Te encuentras con {npc}. ¿Qué harás?")
        accion = input("1. Hablar 2. Comprar 3. Luchar 4. Ignorar > ")
        if accion == "1":
            print(f"{npc} te cuenta un secreto sobre la mazmorra.")
        elif accion == "2":
            print(f"{npc} te ofrece objetos raros por un precio.")
        elif accion == "3":
            npc_personaje = Personaje(npc, 25 + jugador.nivel * 2, 10 + jugador.nivel)
            print(f"{npc} te reta a un combate.")
            combate_por_turnos(jugador, npc_personaje)
        else:
            print(f"Decides ignorar a {npc} y sigues explorando...")

    elif evento == "puerta_cerrada":
        print("¡Has encontrado una puerta cerrada!")
        if random.random() < 0.7:  # 70% de probabilidades de tener una llave en el inventario
            print("¡Tienes la llave! La puerta se abre.")
        else:
            print("La puerta está cerrada y no tienes la llave para abrirla.")

def turno_jugador(jugador, enemigo):
    print(f"\n{MAGENTA}EN COMBATE!{RESET}")
    accion = input("¿Qué haces? [A = Atacar | S = Magia | Z = Objeto | X = Huir]: ").lower() 
    print("")

    if accion == "a":
        print(f"{CYAN}Turno de {jugador.nombre}{RESET}")
        jugador.atacar(enemigo)
        if enemigo.vida <= 0:
            print(f"{RED}¡{enemigo.nombre} ha caído!{RESET}")

    elif accion == "s":
        print(f"{CYAN}Turno de {jugador.nombre}{RESET}")
        jugador.uso_magia(enemigo)
        if enemigo.vida <= 0:
            print(f"{RED}¡{enemigo.nombre} parece estar debilitado por la magia!{RESET}")

    elif accion == "z":
        jugador.usar_objeto(durante_combate=True, enemigo=enemigo)

    elif accion == "x":
        print(f"{YELLOW}¡Has huido del combate!{RESET}")
        return "huir"

    else:
        print(f"{RED}❌ Acción no válida. Pierdes el turno.{RESET}")

def turno_enemigo(enemigo, jugador):
    print(f"\n{RED}Turno Enemigo{RESET}")
    enemigo.atacar(jugador)
    if jugador.vida <= 0:
        print(f"{RED}{jugador.nombre} cae derrotado...{RESET}")

def turno_companero(companero, enemigo):
    print(f"\n{CYAN}{companero.nombre} se prepara para atacar al enemigo...{RESET}")
    companero.atacar(enemigo)
    if enemigo.vida <= 0:
        print(f"{RED}{enemigo.nombre} cae al suelo, derrotado por tu compañero.{RESET}")

def combate_por_turnos(jugador, enemigo):
    separador()
    jugador.bestiario.add(enemigo.nombre)
    print(f"{RED}{BOLD}¡Un combate comienza contra {enemigo.nombre}!{RESET}")
    separador()

    participantes = [jugador]
    if jugador.companero_activo and jugador.companero_activo.esta_vivo():
        participantes.append(jugador.companero_activo)
    participantes.append(enemigo)
    participantes.sort(key=lambda x: x.velocidad, reverse=True)

    while jugador.esta_vivo() and enemigo.esta_vivo():
        for combatiente in participantes:
            if not jugador.esta_vivo() or not enemigo.esta_vivo():
                break
            if not combatiente.esta_vivo():
                continue

            if combatiente == jugador:
                mostrar_estado(jugador, enemigo)
                resultado = turno_jugador(jugador, enemigo)
                if resultado == "huir":
                    return

            elif combatiente == jugador.companero_activo:
                turno_companero(jugador.companero_activo, enemigo)

            elif combatiente == enemigo:
                turno_enemigo(enemigo, jugador)

        # Actualizar participantes vivos
        participantes = [p for p in [jugador, jugador.companero_activo, enemigo] if p and p.esta_vivo()]
        participantes.sort(key=lambda x: x.velocidad, reverse=True)

    # Fin del combate
    if jugador.esta_vivo():
        ganar_combate(jugador, enemigo)
    else:
        pantalla_game_over()

def ganar_combate(jugador, enemigo):
    print(f"\n{GREEN}¡Has derrotado a {enemigo.nombre}!{RESET}")
    exp_ganada = 5 + enemigo.nivel * 3
    jugador.ganar_exp(exp_ganada)

    hallazgo = random.choice([
        Objeto("Tortilla de rescoldo", 
                "utiles", 
                lambda p: p.curacion(p, 15), 
                descripcion="Un clásico del minero, calienta el alma y cura 15 de salud."),
        Objeto("Pico oxidado", "armas", ataque=3),
        Objeto("Casco de minero", "armaduras", defensa=2)
    ])
    jugador.inventario[hallazgo.tipo].append(hallazgo)
    print(f"¡Has encontrado un {hallazgo.nombre} en el cadáver del enemigo!")


def mostrar_titulo():
    separador()
    print(f"{BOLD}{CYAN}Lota's Devil Dungeon{RESET}")
    separador()

def mostrar_menu_principal():
    print(f"{WHITE}1.{CYAN} 🆕 Nueva partida")
    print(f"{WHITE}2.{CYAN} 💾 Cargar partida")
    print(f"{WHITE}3.{CYAN} ❌ Salir{RESET}")
    separador()

def iniciar_nueva_partida():
    historia_inicio()
    nombre = input(f"{MAGENTA}👤 ¿Cuál es tu nombre, valiente héroe?: {RESET}").strip()
    return Personaje(nombre or "Tutin", 30, 10)

def cargar_partida_guardada():
    saves = [f for f in os.listdir() if f.endswith("_save.json")]
    if not saves:
        limpiar_pantalla()
        print(f"{RED}⚠️ No hay partidas guardadas.{RESET}")
        return None

    print(f"{CYAN}📁 Partidas guardadas:{RESET}")
    for i, save in enumerate(saves):
        print(f"  {i + 1}. {save.replace('_save.json', '')}")

    eleccion = input_seguro("> ", 1, len(saves))
    nombre = saves[eleccion - 1].replace("_save.json", "")
    return Personaje.cargar(nombre)


def menu_principal():
    while True:
        mostrar_titulo()
        mostrar_menu_principal()

        opcion = input_seguro(f"{YELLOW}Selecciona una opción (1-3): {RESET}", 1, 3)

        if opcion == 1:
            return iniciar_nueva_partida()

        elif opcion == 2:
            jugador = cargar_partida_guardada()
            if jugador:
                return jugador

        elif opcion == 3:
            print(f"{GREEN}👋 ¡Hasta la próxima!{RESET}")
            exit()
            
def menu_debug(jugador):
    while True:
        separador()
        print(f"{BOLD}{RED}⚙️ MENÚ DE DEBUG (solo dev){RESET}")
        print("1. 🔼 Subir de nivel")
        print("2. ❤️ Restaurar salud y magia")
        print("3. 🎁 Añadir objetos al inventario")
        print("4. 👹 Forzar encuentro con enemigo")
        print("5. 📊 Mostrar estadísticas")
        print("6. ❌ Salir del menú debug")
        separador()

        op = input_seguro("Selecciona una opción de debug: ", 1, 6)
        if op == 1:
            jugador.nivel += 1
            jugador.ganar_exp(0)  # Forzar subida
        elif op == 2:
            jugador.vida = jugador.vida_max
            jugador.magia = jugador.magia_max
            print(f"{GREEN}Salud y magia restauradas.{RESET}")
        elif op == 3:
            jugador.inventario['utiles'].append(Objeto("Pan con Chicharrones", "utiles", lambda p: p.curacion(p, 30)))
            jugador.inventario['armas'].append(Objeto("Martillo de Dev", "armas", ataque=99))
            jugador.inventario['armaduras'].append(Objeto("Chaleco Debug", "armaduras", defensa=99))
            print(f"{CYAN}Objetos debug agregados al inventario.{RESET}")
        elif op == 4:
            enemigo = Personaje("DEBUG DEMONIO", 30, 10, nivel=jugador.nivel + 1, es_enemigo=True)
            combate_por_turnos(jugador, enemigo)
        elif op == 5:
            jugador.mostrar_estadisticas()
        elif op == 6:
            break

def mostrar_menu_aventura():
    separador()
    print(f"{BOLD}{CYAN}🎮 MENÚ DE AVENTURA{RESET}")
    print("1. 🏰 Explorar Mina")
    print("2. 🎒 Ver Inventario")
    print("3. 📜 Ver Bestiario")
    print("4. 💾 Guardar partida")
    print("5. ❌ Salir")
    separador()

def ejecutar_opcion_aventura(eleccion, jugador):
    if eleccion == 1:
        separador()
        escribir_lento(f"{BOLD}{MAGENTA}🔍 Explorando la mina...{RESET}")
        separador()
        explorar_mazmorra(jugador)

    elif eleccion == 2:
        jugador.mostrar_inventario()

    elif eleccion == 3:
        mostrar_bestiario(jugador)

    elif eleccion == 4:
        jugador.guardar()
        print(f"{GREEN}💾 Partida guardada con éxito.{RESET}")

    elif eleccion == 5:
        print(f"{RED}👋 ¡Gracias por jugar!{RESET}")
        return False

    return True

def juego():
    jugador = menu_principal()
    jugando = True

    while jugador.esta_vivo() and jugando:
        mostrar_menu_aventura()
        eleccion = input("Selecciona una opción (1-5, o 0 para debug): ")
        limpiar_pantalla()

        if eleccion == "0":
            menu_debug(jugador)
        elif eleccion.isdigit():
            jugando = ejecutar_opcion_aventura(int(eleccion), jugador)


def mostrar_bestiario(jugador):
    descripciones = {
        "La Viuda del Carbón": "Una figura fantasmal vestida de luto, cuyo llanto ahoga el eco del túnel.",
        "Capataz Zaldívar": "Aún con su casco y látigo, su alma dirige los turnos de los muertos.",
        "El Encapuchado de Humo": "Donde camina, el aire se vuelve espeso y sulfuroso.",
        "El Roto del Derrumbe": "Cubierto de polvo y piedras, se arrastra buscando su pierna perdida.",
        "Niño de la Linterna": "Una linterna parpadea sola en la oscuridad... pero no hay mano que la sujete.",
        "Fantasma del Chiflón": "Los vientos traen su silueta, envuelta en murmullos y quejidos.",
        "Perro del Tajo 7": "Sus ojos brillan como brasas, su cuerpo hecho de sombras mineras.",
        "El Gritón de la Veta": "Grita nombres de obreros desaparecidos... y a veces el tuyo."
    }

    separador()
    print(f"{BOLD}{MAGENTA}📜 BESTIARIO - Enemigos Encontrados:{RESET}\n")
    if not jugador.bestiario:
        print("Aún no has encontrado ningún enemigo.")
    else:
        for nombre in sorted(jugador.bestiario):
            print(f"{YELLOW}- {nombre}:{RESET} {descripciones.get(nombre, 'Sin descripción.')}")
    separador()
    input("Presiona Enter para volver al menú...")

            
def mostrar_game_over():
    print(f"""{BOLD}{RED}
╔═════════════════════════════════════════════╗
║               HAZ MUERTO...                 ║
╠═════════════════════════════════════════════╣
║   Una vez hubo un hombre muerto...          ║
║   que solo queria ver la luz por ultima vez.║
╚═════════════════════════════════════════════╝
{RESET}""")

def pantalla_game_over():
    mostrar_game_over()
    
    while True:
        print(f"{YELLOW}¿Quieres intentarlo de nuevo? (s/n){RESET}")
        eleccion = input("> ").strip().lower()

        if eleccion == "s":
            print(f"{CYAN}🌟 Preparando un nuevo destino...{RESET}\n")
            juego()
            break
        elif eleccion == "n":
            print(f"{RED}Hasta la próxima...{RESET}")
            exit()
        else:
            print(f"{RED}❌ Opción no válida. Escribe 's' o 'n'.{RESET}")

if __name__ == "__main__":
    juego()