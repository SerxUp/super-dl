; Inno Setup script for super-dl. Per-user install, no UAC.
; Build:  iscc /DAppVersion=X.Y.Z installer\super-dl.iss
; CI passes /DAppVersion from the tag; local builds fall back to the value below.

#ifndef AppVersion
  #define AppVersion "0.3.0"
#endif

[Setup]
AppId={{B5F1A3E2-7E1F-4C2B-9A77-5DE000000001}
AppName=super-dl
AppVersion={#AppVersion}
AppPublisher=super-dl
AppPublisherURL=https://github.com/sergioadam/super-dl
DefaultDirName={localappdata}\Programs\super-dl
DefaultGroupName=super-dl
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\super-dl.exe
UninstallDisplayName=super-dl {#AppVersion}
OutputDir=..\dist
OutputBaseFilename=super-dl-setup-{#AppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french";  MessagesFile: "compiler:Languages\French.isl"

[CustomMessages]
english.DesktopIcon=Create a &desktop shortcut
spanish.DesktopIcon=Crear acceso directo en el &escritorio
french.DesktopIcon=Créer un raccourci sur le &bureau
english.LaunchApp=Launch super-dl
spanish.LaunchApp=Iniciar super-dl
french.LaunchApp=Lancer super-dl

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\super-dl.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\super-dl";           Filename: "{app}\super-dl.exe"
Name: "{group}\Uninstall super-dl"; Filename: "{uninstallexe}"
Name: "{autodesktop}\super-dl";     Filename: "{app}\super-dl.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\super-dl.exe"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent
