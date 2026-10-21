Unicode True
!include "MUI2.nsh"
!define APPNAME "海拓表格"
!define VERSION "1.4.1"
Name "${APPNAME} ${VERSION}"
OutFile "HaituoTable_Setup_v${VERSION}_Win64.exe"
InstallDir "$LOCALAPPDATA\Programs\HaituoTable"
RequestExecutionLevel user
ShowInstDetails show
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"
Section "安装"
  SetOutPath "$INSTDIR"
  File "dist\HaituoTable.exe"
  WriteUninstaller "$INSTDIR\卸载.exe"
  CreateDirectory "$SMPROGRAMS\海拓表格"
  CreateShortcut "$SMPROGRAMS\海拓表格\海拓表格.lnk" "$INSTDIR\HaituoTable.exe"
  CreateShortcut "$SMPROGRAMS\海拓表格\卸载.lnk" "$INSTDIR\卸载.exe"
  CreateShortcut "$DESKTOP\海拓表格.lnk" "$INSTDIR\HaituoTable.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HaituoTable" "DisplayName" "海拓表格 ${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HaituoTable" "UninstallString" '"$INSTDIR\卸载.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HaituoTable" "DisplayVersion" "${VERSION}"
SectionEnd
Section "Uninstall"
  Delete "$DESKTOP\海拓表格.lnk"
  Delete "$SMPROGRAMS\海拓表格\海拓表格.lnk"
  Delete "$SMPROGRAMS\海拓表格\卸载.lnk"
  RMDir "$SMPROGRAMS\海拓表格"
  Delete "$INSTDIR\HaituoTable.exe"
  Delete "$INSTDIR\卸载.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HaituoTable"
SectionEnd
