$Source = @'
using System;
using System.Runtime.InteropServices;

public class Program { 
    public static void Run() { 
        DeleteMenu(GetSystemMenu(GetConsoleWindow(), false), SC_CLOSE, MF_BYCOMMAND);
    }
    private const int MF_BYCOMMAND = 0x00000000;
    public const int SC_CLOSE = 0xF060;
    [DllImport("user32.dll")]
    public static extern int DeleteMenu(IntPtr hMenu, int nPosition, int wFlags);
    [DllImport("user32.dll")]
    private static extern IntPtr GetSystemMenu(IntPtr hWnd, bool bRevert);
    [DllImport("kernel32.dll", ExactSpelling = true)]
    private static extern IntPtr GetConsoleWindow();
}
'@
Add-Type -TypeDefinition $Source
[Program]::Run()
