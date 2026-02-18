import os
import subprocess
import winsound
import time

def nuclear_voice_test():
    print("PHASE 1: System Beep")
    winsound.Beep(1000, 500)
    time.sleep(1)

    print("PHASE 2: PowerShell Speech")
    ps_cmd = 'Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak("This is the power shell bridge. Can you hear this?")'
    subprocess.run(["powershell", "-Command", ps_cmd])
    time.sleep(1)

    print("PHASE 3: VBScript Speech")
    vbs_path = "speak.vbs"
    with open(vbs_path, "w") as f:
        f.write('Set sapi = CreateObject("SAPI.SpVoice")\nsapi.Speak "This is the script host bridge. Can you hear this?"')
    subprocess.run(["cscript", "//nologo", vbs_path])
    time.sleep(1)
    os.remove(vbs_path)

    print("PHASE 4: SAPI via Python Directly")
    try:
        import win32com.client
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Speak("This is the direct S API bridge. Can you hear this?")
    except Exception as e:
        print(f"Direct SAPI failed: {e}")

if __name__ == "__main__":
    nuclear_voice_test()
