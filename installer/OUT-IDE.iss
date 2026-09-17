[Setup]
AppName=OUT Language IDE
AppVersion=0.6.3
AppPublisher=OUT Language
DefaultDirName={autopf}\OUT Language
DefaultGroupName=OUT Language
OutputDir=installer
OutputBaseFilename=OUT-IDE-Setup-0.6.3
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
; SetupIconFile=icon.ico
UninstallDisplayIcon={app}\out.exe
LicenseFile=LICENSE.txt
WizardStyle=modern
WizardSizePercent=110
; WizardImageFile=wizard.bmp
; WizardSmallImageFile=wizard_small.bmp

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "associateout"; Description: "Ассоциировать файлы .out с OUT IDE"; GroupDescription: "Ассоциации файлов:"; Flags: checkedonce
Name: "addpath"; Description: "Добавить OUT в PATH (для командной строки)"; GroupDescription: "Системные настройки:"; Flags: unchecked

[Files]
Source: "..\dist\OUT IDE.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\out.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\out-lang\libs\*"; DestDir: "{app}\libs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\samples\*"; DestDir: "{app}\samples"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\OUT IDE"; Filename: "{app}\OUT IDE.exe"
Name: "{group}\Uninstall OUT Language"; Filename: "{uninstallexe}"
Name: "{autodesktop}\OUT IDE"; Filename: "{app}\OUT IDE.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Flags: uninsdeletevalue; Tasks: addpath
Root: HKCU; Subkey: "Software\Classes\.out"; ValueType: string; ValueName: ""; ValueData: "OUTFile"; Flags: uninsdeletevalue; Tasks: associateout
Root: HKCU; Subkey: "Software\Classes\OUTFile"; ValueType: string; ValueName: ""; ValueData: "OUT Language Source"; Flags: uninsdeletekey; Tasks: associateout
Root: HKCU; Subkey: "Software\Classes\OUTFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\OUT IDE.exe"" ""%1"""; Tasks: associateout
Root: HKCU; Subkey: "Software\Classes\OUTFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\out.exe,0"; Tasks: associateout

[Run]
Filename: "{app}\OUT IDE.exe"; Description: "Запустить OUT IDE"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected('addpath') then
    begin
      Exec('cmd.exe', '/c setx PATH "%PATH%;{app}"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;
