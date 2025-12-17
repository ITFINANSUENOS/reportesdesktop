import os

# Extensiones que nos importan (Python, Configs, Markdown, etc.)
EXTENSIONS = {'.py', '.ini', '.toml', '.yaml', '.yml', '.md', '.json', '.env.example'}

# Carpetas a ignorar SIEMPRE
IGNORE_DIRS = {'.git', '__pycache__', 'venv', 'env', 'node_modules', '.idea', '.vscode', 'migrations'}

def is_ignored(path):
    parts = path.split(os.sep)
    return any(p in IGNORE_DIRS for p in parts)

with open('CODIGO_COMPLETO_PARA_GEMINI.txt', 'w', encoding='utf-8') as outfile:
    outfile.write("ESTRUCTURA DEL PROYECTO:\n")
    # Primero escribimos el árbol de directorios para dar contexto
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS] # Filtrar carpetas in situ
        if is_ignored(root): continue
        level = root.replace('.', '').count(os.sep)
        indent = ' ' * 4 * (level)
        outfile.write(f"{indent}{os.path.basename(root)}/\n")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if os.path.splitext(f)[1] in EXTENSIONS:
                outfile.write(f"{subindent}{f}\n")
    
    outfile.write("\n\n" + "="*50 + "\nCONTENIDO DE LOS ARCHIVOS:\n" + "="*50 + "\n\n")

    # Ahora pegamos el código
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        if is_ignored(root): continue
        
        for file in files:
            if os.path.splitext(file)[1] in EXTENSIONS:
                file_path = os.path.join(root, file)
                outfile.write(f"\n\n--- INICIO ARCHIVO: {file_path} ---\n")
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    outfile.write(f"Error leyendo archivo: {e}")
                outfile.write(f"\n--- FIN ARCHIVO: {file_path} ---\n")

print("Listo. Sube el archivo 'CODIGO_COMPLETO_PARA_GEMINI.txt' a Gemini.")