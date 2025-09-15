; Custom NSIS installer script for SimpleCMS File Manager

; Set installer language
!include "MUI2.nsh"

; Custom installer pages
!define MUI_WELCOMEPAGE_TITLE "Welcome to SimpleCMS File Manager"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of SimpleCMS File Manager, a modern file management application."

; Custom finish page
!define MUI_FINISHPAGE_TITLE "Installation Complete"
!define MUI_FINISHPAGE_TEXT "SimpleCMS File Manager has been successfully installed on your computer."

; Add custom installer functions
Function .onInit
  ; Check if the application is already running
  System::Call 'kernel32::CreateMutex(i 0, i 0, t "SimpleCMSFileManager") i .r1 ?e'
  Pop $R0
  StrCmp $R0 0 +3
    MessageBox MB_OK|MB_ICONEXCLAMATION "SimpleCMS File Manager is already running. Please close it before installing."
    Abort
FunctionEnd

Function .onInstSuccess
  ; Optional: Launch the application after installation
  ; Exec "$INSTDIR\SimpleCMS File Manager.exe"
FunctionEnd
