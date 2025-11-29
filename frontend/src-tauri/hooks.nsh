!macro NSIS_HOOK_PREUNINSTALL
  ; Force remove the backend directory (contains .venv and other runtime files)
  RMDir /r "$INSTDIR\backend"
!macroend

