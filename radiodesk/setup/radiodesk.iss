; Inno Setup script for RadioDesk
; Download Inno Setup free at https://jrsoftware.org/isdl.php
; Then run: iscc setup\radiodesk.iss  (from the radiodesk/ root)

#define AppName      "RadioDesk"
#define AppVersion   "1.0.0"
#define AppPublisher "FluffRadio"
#define AppExeName   "RadioDesk.exe"
#define AppIcon      "RadioDesk.ico"
#define DistExe      "..\dist\RadioDesk.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://fluffradio.fr
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=no
OutputDir=..\release
OutputBaseFilename=RadioDesk-Setup-{#AppVersion}
SetupIconFile={#AppIcon}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} - Panneau d'administration FluffRadio

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon";   Description: "Cr&eer une icone sur le Bureau"; GroupDescription: "Icones:"; Flags: unchecked
Name: "quicklaunch";   Description: "Icone dans la &barre des taches"; GroupDescription: "Icones:"; Flags: unchecked

[Files]
Source: "{#DistExe}"; DestDir: "{app}"; DestName: "{#AppExeName}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";       Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Desinstaller {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunch

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Lancer {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\radiodesk-desktop"
