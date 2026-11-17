; =====================================================
;  Audiovane - PUBLIC INSTALLER v1.0
;  by domore100
;  Fully self-contained - no Python needed by user
; =====================================================

#define AppName      "Audiovane"
#define AppShortName "Local TTS"
#define AppVersion   "1.1.0"
#define AppPublisher "domore100"
#define AppExeName   "Audiovane.exe"
#define AppURL       "https://github.com/somore100/audiovane"

[Setup]
AppId={{D4E2A1B3-7F6C-4A8D-9E0B-2C5F8A3D1E7F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={autopf}\Audiovane
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=setup_output
OutputBaseFilename=Audiovane_Setup_v{#AppVersion}
SetupIconFile=logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=no
LicenseFile=LICENSE.txt
MinVersion=10.0
PrivilegesRequired=admin
UninstallDisplayIcon={app}\logo.ico
UninstallDisplayName={#AppName} {#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut (named ""Local TTS"")"; GroupDescription: "Shortcuts:"
Name: "startmenu"; Description: "Add to Start Menu"; GroupDescription: "Shortcuts:"
Name: "install_models"; Description: "Download basic AI models now (Whisper STT ~150MB + VCTK voices ~100MB) - requires internet"; GroupDescription: "AI Models:"
Name: "install_xtts"; Description: "Also download multilingual voices XTTS-v2 (~2GB) - optional, for Slovenian/Russian etc"; GroupDescription: "AI Models:"

[Dirs]
Name: "{app}"
Name: "{app}\python"
Name: "{app}\models\vctk"
Name: "{app}\models\xtts_v2"
Name: "{app}\models\whisper"
Name: "{app}\models\vosk"

[Files]
; Main application
Source: "dist\Audiovane\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "logo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "download_models.py"; DestDir: "{app}"; Flags: ignoreversion
; Bundled Python 3.12 for model downloading
Source: "python_bundled\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\logo.ico"; Tasks: startmenu
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppShortName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon

[Run]
; The bundled Python is only needed by download_models.py, so install its
; packages (same pins as requirements.txt) only when a model download is chosen.
Filename: "{app}\python\python.exe"; Parameters: "-m pip install torch==2.10.0 torchaudio==2.10.0 --index-url https://download.pytorch.org/whl/cpu"; StatusMsg: "Installing PyTorch (large download)..."; Flags: runhidden waituntilterminated; Tasks: install_models install_xtts
Filename: "{app}\python\python.exe"; Parameters: "-m pip install ""certifi>=2026.10.18"" ""coqui-tts[codec]"" ""transformers>=4.46,<4.57"" openai-whisper"; StatusMsg: "Installing packages..."; Flags: runhidden waituntilterminated; Tasks: install_models install_xtts
; Download basic models if selected
Filename: "{app}\python\python.exe"; Parameters: """{app}\download_models.py"" --whisper --vctk"; StatusMsg: "Downloading basic AI models (Whisper + VCTK, ~250MB)..."; WorkingDir: "{app}"; Flags: runhidden waituntilterminated; Tasks: install_models
; Download XTTS if selected  
Filename: "{app}\python\python.exe"; Parameters: """{app}\download_models.py"" --xtts"; StatusMsg: "Downloading multilingual voices (~2GB, this takes a while)..."; WorkingDir: "{app}"; Flags: runhidden waituntilterminated; Tasks: install_xtts

Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Messages]
WelcomeLabel1=Welcome to Audiovane
WelcomeLabel2=Version {#AppVersion} by {#AppPublisher}%n%nFully offline text-to-speech and speech-to-text.%n%n  Supports Slovenian, English, Russian and more%n  No Python installation required%n  English voices (VCTK) + multilingual XTTS-v2%n  Offline speech recognition via Whisper%n%nNote: Setup downloads ~2.5GB of AI models.%nPlease have internet and 5GB free disk space.%n%nClick Next to continue.
FinishedLabel=Audiovane has been installed!%n%nDesktop shortcut "Local TTS" has been created.%n%nClick Finish to close.

[Code]
