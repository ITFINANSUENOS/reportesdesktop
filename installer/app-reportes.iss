; ---------------------------------------------------------------------------
; installer/app-reportes.iss
; Instalador de "Reportes Financieros" (Inno Setup).
;
; MOTIVO: el .exe compilado (carpeta dist\app-reportes) se instala formalmente
; en cada PC con accesos directos y desinstalador. Instalación POR USUARIO
; (sin permisos de administrador) en %LOCALAPPDATA%\Programs.
; La app escribe sus logs en %LOCALAPPDATA%\app-reportes\logs, por lo que no
; depende de que esta carpeta sea de solo lectura.
; ---------------------------------------------------------------------------
#define MyAppName "Reportes Financieros"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Departamento Financiero"
#define MyAppExeName "app-reportes.exe"

[Setup]
AppId={{8C3F6E2A-1B4D-4A9E-8F5C-2A7D9B41C6E0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Reportes Financieros
DefaultGroupName={#MyAppName}
; Instalación para el usuario actual: no pide administrador (pero se permite
; elegir "todos los usuarios" si el usuario sí tiene permisos).
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist\instalador
OutputBaseFilename=ReportesFinancieros-setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\src\icons\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Files]
; Carpeta autocontenida del .exe (todas las librerías deben viajar juntas).
Source: "..\dist\app-reportes\app-reportes.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\app-reportes\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName}"; Flags: nowait postinstall skipifsilent
