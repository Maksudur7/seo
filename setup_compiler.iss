; ====================================================================
; Inno Setup Script for Meta Threads SEO Bot Standalone Installer
; Creates a single Threads_SEO_Bot_Setup.exe Professional Installer
; ====================================================================

[Setup]
AppName=Meta Threads SEO Bot
AppVersion=1.0.0
DefaultDirName={autopf}\Threads_SEO_Bot
DefaultGroupName=Meta Threads SEO Bot
OutputDir=.\installer_dist
OutputBaseFilename=Threads_SEO_Bot_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Start_Threads_Bot.bat

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Meta Threads SEO Bot"; Filename: "{app}\Start_Threads_Bot.bat"
Name: "{autodesktop}\Meta Threads SEO Bot"; Filename: "{app}\Start_Threads_Bot.bat"; Tasks: desktopicon

[Run]
Filename: "{app}\Install_And_Start.bat"; Description: "Launch Meta Threads SEO Bot Now"; Flags: postinstall shellexec skipifsilent
