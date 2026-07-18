import os
import sys
import PyInstaller.__main__

def build_executable():
    print("Iniciando processo de empacotamento do Carimbo.pdf...")
    
    # Ponto de entrada do FastAPI
    entry_script = os.path.join("app", "main.py")
    
    # Mapeamento do template para o pacote executável.
    # No Windows, o separador do PyInstaller para add-data é ";"
    add_data_param = "app/templates;app/templates"
    
    args = [
        entry_script,
        "--onefile",
        "--name=carimbo-pdf",
        f"--add-data={add_data_param}",
        "--clean",
    ]
    
    print(f"Executando PyInstaller com os argumentos: {args}")
    try:
        PyInstaller.__main__.run(args)
        print("\nEmpacotamento concluído com sucesso!")
        print("O arquivo executável portátil único foi gerado em: dist/carimbo-pdf.exe")
    except Exception as e:
        print(f"Erro durante o processo de build: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_executable()
