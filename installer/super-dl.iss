; Inno Setup script for super-dl. Per-user install, no UAC.
; Build:  iscc /DAppVersion=X.Y.Z installer\super-dl.iss
; CI passes /DAppVersion from the tag; local builds fall back to the value below.

#ifndef AppVersion
  #define AppVersion "0.2.2"
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

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\super-dl.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\super-dl";           Filename: "{app}\super-dl.exe"
Name: "{group}\Uninstall super-dl"; Filename: "{uninstallexe}"
Name: "{autodesktop}\super-dl";     Filename: "{app}\super-dl.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\super-dl.exe"; Description: "Launch super-dl"; Flags: nowait postinstall skipifsilent
