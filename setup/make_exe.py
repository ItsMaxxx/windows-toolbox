"""
Creates a copy of pythonw.exe with its own name and icon, e.g. runtime\\HardwareMonitor.exe.
Called by setup.ps1 (step 3) with the Python from runtime\\:

    python make_exe.py <target.exe> <description> <icon.ico>

What for: the Task Manager shows the file description of the .exe as the program name and its icon next to it. A plain
copy of pythonw.exe would be called "Python" there with the Python logo. That's why two resources are replaced in
the copy:
  - the version info (file description = <description>, e.g. "Hardware Monitor")
  - the icon (from <icon.ico>)
The digital signature of pythonw.exe is removed in the process – after the change it would be invalid anyway, and an
invalid signature looks more suspicious to virus scanners than none at all.

Changes are made via the Windows functions BeginUpdateResource/UpdateResource/EndUpdateResource (kernel32) –
no extra tool needed.

Exit code: 0 = created or already up to date, 1 = error, 2 = target currently in use (program is running).
"""

import ctypes
import os
import struct
import sys
from ctypes import wintypes
from pathlib import Path

RT_ICON, RT_GROUP_ICON, RT_VERSION = 3, 14, 16
LANGUAGE = 1033                                  # language of the resources in pythonw.exe (English, USA)
PRODUCT = "Toolbox"
COMPANY = "Windows Toolbox"                      # publisher (Task Manager → Startup apps, Properties)

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.BeginUpdateResourceW.restype = wintypes.HANDLE
k32.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
k32.UpdateResourceW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, wintypes.WORD, ctypes.c_void_p,
                                wintypes.DWORD]
k32.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
k32.LoadLibraryExW.restype = wintypes.HMODULE
k32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
k32.FreeLibrary.argtypes = [wintypes.HMODULE]
k32.EnumResourceNamesW.argtypes = [wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
ENUM_NAMES = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)


def error(text):
    raise OSError(f"{text} (Windows error {ctypes.get_last_error()})")


# ---------- Remove signature ----------
def without_signature(data):
    """pythonw.exe without the signature: clear the "Security" entry in the data directory, cut off the data at the end
    of the file."""
    data = bytearray(data)
    pe = struct.unpack_from("<I", data, 0x3C)[0]                        # start of the PE header
    magic = struct.unpack_from("<H", data, pe + 24)[0]                  # 0x20B = 64 bit, 0x10B = 32 bit
    entry = pe + 24 + (112 if magic == 0x20B else 96) + 4 * 8           # data directory no. 4 = Security
    offset, size = struct.unpack_from("<II", data, entry)
    if offset and offset + size == len(data):                           # the signature is always at the end
        del data[offset:]
        struct.pack_into("<II", data, entry, 0, 0)
    return bytes(data)


# ---------- Version info ----------
def node(name, value=b"", children=(), text=False):
    """A block of the version info (VS_VERSIONINFO, StringFileInfo, …): length, value length, type, name, value,
    sub-blocks. Everything is aligned to 4 bytes."""
    def pad(b):
        return b + b"\0" * (-len(b) % 4)

    header_rest = pad(b"\0" * 6 + (name + "\0").encode("utf-16-le"))[6:]
    body = header_rest + value
    if children:
        body = pad(b"\0" * 6 + body)[6:] + b"".join(pad(c) for c in children[:-1]) + children[-1]
    value_length = len(value) // 2 if text else len(value)              # for text in characters, otherwise in bytes
    return struct.pack("<HHH", 6 + len(body), value_length, 1 if text else 0) + body


def version_info(description, file_name):
    v = sys.version_info
    ms, ls = (v.major << 16) | v.minor, v.micro << 16
    fixed = struct.pack("<13I", 0xFEEF04BD, 0x00010000, ms, ls, ms, ls, 0x3F, 0, 0x40004, 1, 0, 0, 0)
    version = f"{v.major}.{v.minor}.{v.micro}"
    texts = {
        "FileDescription": description,
        "ProductName": PRODUCT,
        "CompanyName": COMPANY,
        "FileVersion": version,
        "ProductVersion": version,
        "InternalName": Path(file_name).stem,
        "OriginalFilename": file_name,
        "Comments": f"pythonw.exe (Python {version}) with its own name and icon – created by Setup.exe",
        "LegalCopyright": "Python: Copyright © Python Software Foundation",
    }
    entries = [node(k, (w + "\0").encode("utf-16-le"), text=True) for k, w in texts.items()]
    table = node(f"{LANGUAGE:04X}04B0", children=entries, text=True)     # 04B0 = Unicode
    return node("VS_VERSION_INFO", fixed, children=[
        node("StringFileInfo", children=[table], text=True),
        node("VarFileInfo", children=[node("Translation", struct.pack("<HH", LANGUAGE, 1200))], text=True),
    ])


# ---------- Icon ----------
def icon_parts(ico):
    """.ico -> (images for RT_ICON, directory for RT_GROUP_ICON). The directory refers to the images by number."""
    _, kind, count = struct.unpack_from("<HHH", ico, 0)
    if kind != 1:
        raise ValueError("not an .ico file")
    images, directory = [], struct.pack("<HHH", 0, 1, count)
    for i in range(count):
        w, h, colors, _, planes, bits, size, offset = struct.unpack_from("<BBBBHHII", ico, 6 + 16 * i)
        images.append(ico[offset:offset + size])
        directory += struct.pack("<BBBBHHIH", w, h, colors, 0, planes, bits, size, i + 1)
    return images, directory


def existing(path, kind):
    """Numbers of the resources of one type in an .exe (e.g. the 12 Python icon images)."""
    module = k32.LoadLibraryExW(str(path), None, 0x2)                   # LOAD_LIBRARY_AS_DATAFILE
    if not module:
        error(f"{path} can't be read")
    numbers = []
    callback = ENUM_NAMES(lambda m, t, name, _: numbers.append(name) or True)
    k32.EnumResourceNamesW(module, kind, callback, None)                # False if there are none – fine too
    k32.FreeLibrary(module)
    return [n for n in numbers if n < 0x10000]                          # only numbers, no names


def resource(handle, kind, number, data):
    """Set a resource or delete it with data=None."""
    buffer = ctypes.create_string_buffer(data, len(data)) if data is not None else None
    if not k32.UpdateResourceW(handle, kind, number, LANGUAGE, buffer, len(data) if data else 0):
        error(f"resource {kind}/{number} can't be changed")


def forget_names(target):
    """Windows remembers program names in the "MuiCache" – for an earlier plain copy it would still say "Python" there,
    and the Task Manager would keep showing the old name. Delete the entry, then Windows reads the name from the file
    again. Then tell the shell that the file has changed, so it reads the icon again too."""
    import winreg
    key = r"Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
            for suffix in (".FriendlyAppName", ".ApplicationCompany"):
                try:
                    winreg.DeleteValue(k, str(target.resolve()) + suffix)
                except FileNotFoundError:
                    pass
    except OSError:
        pass                                     # no MuiCache – nothing to forget
    # The same for the icon: Windows keeps it cached (the Task Manager would otherwise keep showing the
    # Python logo). SHCNE_UPDATEITEM tells the shell that the file has changed -> read the icon again.
    ctypes.windll.shell32.SHChangeNotify(0x00002000, 0x0005, ctypes.c_wchar_p(str(target.resolve())), None)  # PATHW


# ---------- Procedure ----------
def create(target, description, ico_path):
    source = Path(sys.executable).with_name("pythonw.exe")
    new = target.with_name(target.name + ".new")
    new.write_bytes(without_signature(source.read_bytes()))
    try:
        images, directory = icon_parts(ico_path.read_bytes())
        old_images = existing(new, RT_ICON)
        handle = k32.BeginUpdateResourceW(str(new), False)
        if not handle:
            error("BeginUpdateResource failed")
        for number in existing(new, RT_GROUP_ICON):
            resource(handle, RT_GROUP_ICON, number, None)               # Python icon out …
        for number in old_images:
            if number > len(images):
                resource(handle, RT_ICON, number, None)
        for number, image in enumerate(images, start=1):                # … our own in
            resource(handle, RT_ICON, number, image)
        resource(handle, RT_GROUP_ICON, 1, directory)
        resource(handle, RT_VERSION, 1, version_info(description, target.name))
        if not k32.EndUpdateResourceW(handle, False):
            error("EndUpdateResource failed")

        if target.exists() and target.read_bytes() == new.read_bytes():
            forget_names(target)                 # even then: an earlier run may not have done it yet
            print(f"{target.name} is already up to date")
            return 0
        try:
            os.replace(new, target)
        except PermissionError:
            print(f"{target.name} is currently in use – set up again after quitting the program")
            return 2
        forget_names(target)
        print(f"{target.name} created")
        return 0
    finally:
        new.unlink(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    try:
        sys.exit(create(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])))
    except (OSError, ValueError) as e:
        print(f"Error: {e}")
        sys.exit(1)
