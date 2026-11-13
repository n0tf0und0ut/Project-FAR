"""FAR-SQLITE-REAL-CONTRACT-001: replay actual SQLite semantics; Research only.

Two bindings to the SAME SQLite engine test the exact six-case contract.
Python-only standard library. No model-generated ground truth.
"""
import ctypes
import ctypes.util
import json
import sqlite3

CASES = [
    ("null", None), ("integer_zero", 0), ("integer_one", 1),
    ("text_zero", "0"), ("text_one", "1"), ("text_other", "x"),
]
SQL = [
    "SELECT ? IS NULL", "SELECT ? = 0", "SELECT ? = 1",
    "SELECT ? = '0'",  # Explicit contract extension, not a blinded holdout
]
EXPECTED = {
    "null": (1, None, None, None),
    "integer_zero": (0, 1, 0, 0),
    "integer_one": (0, 0, 1, 0),
    "text_zero": (0, 0, 0, 1),
    "text_one": (0, 0, 0, 0),
    "text_other": (0, 0, 0, 0),
}

def python_engine():
    db = sqlite3.connect(":memory:")
    try:
        sid = db.execute("SELECT sqlite_source_id()").fetchone()[0]
        rows = {k: tuple(db.execute(q, (v,)).fetchone()[0] for q in SQL)
                for k, v in CASES}
        return (sqlite3.sqlite_version, sid), rows
    finally:
        db.close()

def c_engine():
    path = ctypes.util.find_library("sqlite3")
    if not path:
        raise RuntimeError("native SQLite library absent; fail closed")
    lib = ctypes.CDLL(path)
    P, I, S = ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p
    def api(name, restype, *args):
        fn = getattr(lib, name)
        fn.restype = restype
        fn.argtypes = list(args)
        return fn
    op = api("sqlite3_open", I, S, ctypes.POINTER(P))
    close = api("sqlite3_close", I, P)
    prepare = api("sqlite3_prepare_v2", I, P, S, I, ctypes.POINTER(P), ctypes.POINTER(S))
    bind_null = api("sqlite3_bind_null", I, P, I)
    bind_int = api("sqlite3_bind_int64", I, P, I, ctypes.c_int64)
    bind_text = api("sqlite3_bind_text", I, P, I, S, I, P)
    step = api("sqlite3_step", I, P)
    col_type = api("sqlite3_column_type", I, P, I)
    col_int = api("sqlite3_column_int64", ctypes.c_int64, P, I)
    finalize = api("sqlite3_finalize", I, P)
    version = api("sqlite3_libversion", S)
    sourceid = api("sqlite3_sourceid", S)
    db = P()
    if op(b":memory:", ctypes.byref(db)) != 0:
        raise RuntimeError("native SQLite open failed")
    try:
        identity = (version().decode(), sourceid().decode())
        rows = {}
        for key, value in CASES:
            result = []
            for sql in SQL:
                stmt = P()
                if prepare(db, sql.encode(), -1, ctypes.byref(stmt), None) != 0:
                    raise RuntimeError("native prepare failed")
                try:
                    if value is None:
                        rc = bind_null(stmt, 1)
                    elif type(value) is int:
                        rc = bind_int(stmt, 1, value)
                    elif type(value) is str:
                        buf = value.encode()
                        rc = bind_text(stmt, 1, buf, len(buf), P(-1))
                    else:
                        raise TypeError(type(value).__name__)
                    if rc != 0 or step(stmt) != 100:
                        raise RuntimeError("native SQLite bind/step failed")
                    t = col_type(stmt, 0)
                    if t not in (1, 5):
                        raise RuntimeError("unexpected result type")
                    result.append(None if t == 5 else int(col_int(stmt, 0)))
                finally:
                    if finalize(stmt) != 0:
                        raise RuntimeError("native SQLite finalize failed")
            rows[key] = tuple(result)
        return identity, rows
    finally:
        if close(db) != 0:
            raise RuntimeError("native SQLite close failed")

def code(key):
    if key == "null":
        return "missing"
    if key == "integer_zero":
        return "number_zero"
    if key == "integer_one":
        return "number_one"
    return "other"

def storage_class(key):
    if key == "null":
        return "null"
    if key.startswith("integer_"):
        return "integer"
    return "text"

def verify():
    py_id, py = python_engine()
    c_id, native = c_engine()
    if py_id != c_id or py != native:
        raise AssertionError("API paths or source IDs disagree")
    if py != EXPECTED:
        raise AssertionError("observed SQLite results violate documented finite expectations")
    names = [key for key, _ in CASES]
    if len(set(tuple(py[k][:3]) for k in names)) != 4:
        raise AssertionError("incorrect quotient rank")
    for a in names:
        for b in names:
            if (code(a) == code(b)) != (py[a][:3] == py[b][:3]):
                raise AssertionError("exact minimality failure")
    if not (storage_class("integer_zero") == storage_class("integer_one")
            and py["integer_zero"][:3] != py["integer_one"][:3]):
        raise AssertionError("negative type-bucket control failed")
    if not (code("text_zero") == code("text_one")
            and py["text_zero"][:3] == py["text_one"][:3]
            and py["text_zero"][3] != py["text_one"][3]):
        raise AssertionError("expanded-contract counterexample failed")
    return {
        "status": "PASS at six-case three-query exact scope",
        "sqlite_version": py_id[0],
        "sqlite_source_id": py_id[1],
        "cases": names,
        "rows_with_one_additional_query": {k: list(py[k]) for k in names},
        "distinct_pairs_checked": 15,
        "ordered_pairs_checked": 36,
        "primary_quotient_rank": 4,
        "storage_class_loss_confirmed": True,
        "extended_contract_loss_confirmed": True,
    }

if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
