"""PrusaSlicer 2.7.2 --info text + G-code footer -> one JSON record (slice.sh writes slice-report.json with it).
Usage: python3 slice_report.py <info.txt> <file.gcode> <slice-log.txt> > slice-report.json"""
import json, re, sys


def parse_info(text):
    kv = dict(re.findall(r"^\s*(\w+)\s*=\s*(.+?)\s*$", text, re.M))
    num = lambda k, f=float: f(kv[k]) if k in kv else None
    return {k: v for k, v in {"size_z_mm": num("size_z"), "facets": num("number_of_facets", int),
            "manifold": kv.get("manifold") == "yes", "open_edges": num("open_edges", int) or 0,
            "parts": num("number_of_parts", int), "volume_mm3": num("volume")}.items() if v is not None}


def parse_gcode(text):
    foot = dict(re.findall(r"^; ([^=\n]+?) = (.+)$", text, re.M))
    t = foot.get("estimated printing time (normal mode)", "")
    parts = dict((u, int(n)) for n, u in re.findall(r"(\d+)([dhms])", t))
    minutes = parts.get("d", 0) * 1440 + parts.get("h", 0) * 60 + parts.get("m", 0) + parts.get("s", 0) / 60
    return {"layers": len(re.findall(r"^;LAYER_CHANGE", text, re.M)),
            "filament_mm": float(foot["filament used [mm]"]) if "filament used [mm]" in foot else None,
            "filament_g": float(foot["filament used [g]"]) if "filament used [g]" in foot else None,
            "print_time": t or None, "print_time_min": round(minutes, 2) if t else None}


if __name__ == "__main__":
    info, gcode, log = (open(p, encoding="utf-8", errors="replace").read() for p in sys.argv[1:4])
    warnings = [l for l in log.splitlines() if "=>" not in l and "exported to" not in l and l.strip()]
    print(json.dumps({"info_before_repair": parse_info(info), "gcode": parse_gcode(gcode),
                      "slicer_messages": warnings}, indent=1))
