# Creates the Start-menu shortcut "Intern Prep Studio" (with the app icon) that can be pinned to the taskbar.
# Run again if this folder is moved:   pwsh -File scripts\install_windows_shortcut.ps1
#
# The shortcut carries the same AppUserModelID that Chrome/Edge give the app window, so the running
# window sits on the pinned icon instead of opening a second taskbar button.
$root = Split-Path -Parent $PSScriptRoot
$vbs = Join-Path $root 'Intern Prep Studio.vbs'
$ico = Join-Path $root 'assets\icon.ico'
$lnk = Join-Path ([Environment]::GetFolderPath('Programs')) 'Intern Prep Studio.lnk'

# Same choice as find_windows_browser() in launcher.pyw: Chrome only if it is the default browser.
$chrome = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
            "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe") | Where-Object { Test-Path $_ }
$edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
          "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ }
$default = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice' -ErrorAction SilentlyContinue).ProgId
$useChrome = $chrome -and (($default -match 'chrome') -or -not $edge)
$appId = ($useChrome ? 'Chrome' : 'MSEdge') + '.localhost_/'

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

public static class PrepShortcut {
    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    struct PROPERTYKEY { public Guid fmtid; public uint pid; }

    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPropertyStore {
        int GetCount(out uint c);
        int GetAt(uint i, out PROPERTYKEY k);
        int GetValue(ref PROPERTYKEY k, IntPtr v);
        int SetValue(ref PROPERTYKEY k, IntPtr v);
        int Commit();
    }

    [ComImport, Guid("000214F9-0000-0000-C000-000000000046"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IShellLinkW {
        void GetPath(IntPtr a, int b, IntPtr c, uint d);
        void GetIDList(out IntPtr a);
        void SetIDList(IntPtr a);
        void GetDescription(IntPtr a, int b);
        void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string s);
        void GetWorkingDirectory(IntPtr a, int b);
        void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string s);
        void GetArguments(IntPtr a, int b);
        void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string s);
        void GetHotkey(out short a);
        void SetHotkey(short a);
        void GetShowCmd(out int a);
        void SetShowCmd(int a);
        void GetIconLocation(IntPtr a, int b, out int c);
        void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string s, int i);
        void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string s, uint r);
        void Resolve(IntPtr h, uint f);
        void SetPath([MarshalAs(UnmanagedType.LPWStr)] string s);
    }

    [DllImport("propsys.dll", CharSet = CharSet.Unicode)]
    static extern int InitPropVariantFromStringVector([MarshalAs(UnmanagedType.LPArray)] string[] a, uint n, IntPtr v);
    [DllImport("ole32.dll")] static extern int PropVariantClear(IntPtr v);

    public static void Create(string lnk, string target, string args, string workDir, string icon, string appId) {
        object link = Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("00021401-0000-0000-C000-000000000046")));
        IShellLinkW sl = (IShellLinkW)link;
        sl.SetPath(target);
        sl.SetArguments(args);
        sl.SetWorkingDirectory(workDir);
        sl.SetIconLocation(icon, 0);
        sl.SetDescription("Intern Prep Studio");

        IntPtr pv = Marshal.AllocCoTaskMem(24);
        try {
            for (int i = 0; i < 24; i++) Marshal.WriteByte(pv, i, 0);
            Marshal.WriteInt16(pv, 0, 31);                                  // VT_LPWSTR
            Marshal.WriteIntPtr(pv, 8, Marshal.StringToCoTaskMemUni(appId));
            PROPERTYKEY key = new PROPERTYKEY { fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), pid = 5 };  // System.AppUserModel.ID
            IPropertyStore ps = (IPropertyStore)link;
            Marshal.ThrowExceptionForHR(ps.SetValue(ref key, pv));
            Marshal.ThrowExceptionForHR(ps.Commit());
        } finally { PropVariantClear(pv); Marshal.FreeCoTaskMem(pv); }
        ((IPersistFile)link).Save(lnk, true);
    }
}
'@

[PrepShortcut]::Create($lnk, "$env:SystemRoot\System32\wscript.exe", "`"$vbs`"", $root, $ico, $appId)
"Created $lnk  (AppUserModelID: $appId)"
