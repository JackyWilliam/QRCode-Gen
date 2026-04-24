; QRCode Gen Windows Installer (NSIS)
; 通过 installer/build.sh 编译。APP_VERSION 和 SOURCE_DIR 由 -D 注入。

Unicode true
SetCompressor /SOLID lzma

!ifndef APP_VERSION
  !define APP_VERSION "0.0.0"
!endif
!ifndef SOURCE_DIR
  !define SOURCE_DIR "QRCode Gen"
!endif
!ifndef ICON_FILE
  !define ICON_FILE "Logo.ico"
!endif

!define APP_NAME        "QRCode Gen"
!define APP_PUBLISHER   "Yijie Ding"
!define APP_WEBSITE     "https://github.com/JackyWilliam/QRCode-Gen"
!define APP_EXE         "QRCode Gen.exe"
!define APP_DIR_NAME    "QRCode Gen"
!define APP_UNINST_KEY  "Software\Microsoft\Windows\CurrentVersion\Uninstall\QRCodeGen"

!include "MUI2.nsh"
!include "FileFunc.nsh"

Name            "${APP_NAME}"
OutFile         "QRCode Gen Setup v${APP_VERSION}.exe"
InstallDir      "$PROGRAMFILES64\${APP_DIR_NAME}"
InstallDirRegKey HKLM "Software\${APP_DIR_NAME}" "InstallDir"
RequestExecutionLevel admin
BrandingText    "${APP_NAME} v${APP_VERSION}"

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey  "ProductName"     "${APP_NAME}"
VIAddVersionKey  "CompanyName"     "${APP_PUBLISHER}"
VIAddVersionKey  "FileVersion"     "${APP_VERSION}"
VIAddVersionKey  "ProductVersion"  "${APP_VERSION}"
VIAddVersionKey  "FileDescription" "${APP_NAME} Installer"
VIAddVersionKey  "LegalCopyright"  "Copyright (C) 2026 ${APP_PUBLISHER}. MIT License."

!define MUI_ABORTWARNING
!define MUI_ICON                    "${ICON_FILE}"
!define MUI_UNICON                  "${ICON_FILE}"
!define MUI_FINISHPAGE_RUN          "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT     "Launch ${APP_NAME}"

; ---- Install pages ----
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; ---- Uninstall pages ----
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ---- Languages (order sets the chooser default) ----
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

; ---- Sections ----
Section "Application (required)" SEC_APP
  SectionIn RO
  SetOutPath "$INSTDIR"
  File /r "${SOURCE_DIR}\*.*"

  ; Registry for Add/Remove Programs
  WriteRegStr HKLM "${APP_UNINST_KEY}" "DisplayName"     "${APP_NAME}"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "DisplayVersion"  "${APP_VERSION}"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "Publisher"       "${APP_PUBLISHER}"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "URLInfoAbout"    "${APP_WEBSITE}"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "DisplayIcon"     "$INSTDIR\${APP_EXE}"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKLM "${APP_UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKLM "${APP_UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${APP_UNINST_KEY}" "NoRepair" 1

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${APP_UNINST_KEY}" "EstimatedSize" "$0"

  WriteRegStr HKLM "Software\${APP_DIR_NAME}" "InstallDir" "$INSTDIR"

  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Start Menu shortcut" SEC_STARTMENU
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"   "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortCut  "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"     "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Desktop shortcut" SEC_DESKTOP
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
SectionEnd

LangString DESC_APP        ${LANG_SIMPCHINESE} "主程序文件（必装）"
LangString DESC_APP        ${LANG_ENGLISH}     "Application files (required)"
LangString DESC_STARTMENU  ${LANG_SIMPCHINESE} "创建开始菜单快捷方式"
LangString DESC_STARTMENU  ${LANG_ENGLISH}     "Create Start Menu shortcut"
LangString DESC_DESKTOP    ${LANG_SIMPCHINESE} "创建桌面快捷方式"
LangString DESC_DESKTOP    ${LANG_ENGLISH}     "Create Desktop shortcut"

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_APP}       $(DESC_APP)
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_STARTMENU} $(DESC_STARTMENU)
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_DESKTOP}   $(DESC_DESKTOP)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ---- Uninstall ----
Section "Uninstall"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
  RMDir  "$SMPROGRAMS\${APP_NAME}"

  RMDir /r "$INSTDIR"

  DeleteRegKey HKLM "${APP_UNINST_KEY}"
  DeleteRegKey HKLM "Software\${APP_DIR_NAME}"
SectionEnd

Function .onInit
  System::Call 'kernel32::CreateMutex(p 0, i 0, t "QRCodeGenInstallerMutex") i .r1 ?e'
  Pop $R0
  StrCmp $R0 0 +3
    MessageBox MB_OK|MB_ICONEXCLAMATION "Installer is already running."
    Abort
FunctionEnd
