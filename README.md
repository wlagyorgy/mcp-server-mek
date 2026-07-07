# MEK MCP

Python MCP szerver a [Magyar Elektronikus Könyvtár](https://www.mek.oszk.hu/) keresőinek eléréséhez agentic eszközök számára.

## Dokumentáció

- [Architektúra](docs/architecture.md)

## MCP toolok

| Tool | Leírás |
|------|--------|
| `mek_search_simple` | Egyszerű metaadat-keresés (szerző, cím, téma, MEK ID) |
| `mek_search_fulltext` | Teljes szöveg keresés HTML/PDF dokumentumokban |
| `mek_search_advanced` | Összetett keresés — max. 5 mezősor, AND/OR/NOT (Playwright scraping) |
| `mek_list_search_fields` | Elérhető mező-aliasok és fulltext témakörök |

### Találati limitek

| Keresés | Default | Lapozás |
|---------|---------|---------|
| Egyszerű / fulltext | `page_size=10` (max 100) | `page` paraméterrel |
| Összetett | `max_results=50` | Nincs — a MEK egy listában adja vissza az összes találatot |

Minden válasz tartalmazza a `total_hits` értéket (teljes találatszám) és a `documents` szeletet (amit az LLM kap).

## Telepítés

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
playwright install chromium
```

Az összetett kereséshez **Playwright + Chromium** szükséges (headless böngésző scraping a `detailed` oldalhoz).

## Tesztelés

```bash
pytest -m "not network"    # offline tesztek
pytest -m network          # élő MEK hálózati tesztek
```

## Cursor MCP konfiguráció

A projekt tartalmazza: [`.cursor/mcp.json`](.cursor/mcp.json)

```json
{
  "mcpServers": {
    "mek": {
      "command": "${workspaceFolder}/.venv/Scripts/python.exe",
      "args": ["-m", "mek_mcp.server"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

Előfeltétel: `pip install -e ".[dev]"` a `.venv`-ben. Cursorban: **Settings → MCP** → a `mek` szerver engedélyezése.

## Render deploy (Streamable HTTP)

### Docker (ajánlott)

```bash
docker build -t mek-mcp .
docker run --rm -p 10000:10000 -e MCP_TRANSPORT=streamable-http -e HOST=0.0.0.0 mek-mcp
```

Health check: `http://localhost:10000/health`

MCP végpont: `http://localhost:10000/mcp`

### Render Web Service

1. Push a repót GitHubra
2. Render Dashboard → **New → Blueprint** → válaszd a `render.yaml`-t  
   *(vagy **New → Web Service** → Docker runtime, `Dockerfile` útvonal)*
3. A `PORT` változót a Render automatikusan beállítja

| Változó | Érték |
|---------|--------|
| `MCP_TRANSPORT` | `streamable-http` |
| `HOST` | `0.0.0.0` |
| `MEK_PLAYWRIGHT_HEADLESS` | `true` |
| `MEK_SCRAPE_TIMEOUT_MS` | `90000` |

Start command (Dockerfile-ből automatikus): `python -m mek_mcp.server`

Health check: `GET /health`

MCP végpont (alapértelmezés):

- Streamable HTTP: `https://<service>.onrender.com/mcp`

Legacy SSE (opcionális, `MCP_TRANSPORT=sse`):

- SSE stream: `https://<service>.onrender.com/sse`
- Üzenetek: `https://<service>.onrender.com/messages/`

A Playwright Chromium a Docker image része (`mcr.microsoft.com/playwright/python`).

## Fejlesztés: űrlap-paraméterek feltárása

```bash
python scripts/discover_forms.py --probe
```

A riport: `discovery/output/forms_report.json`

## Licenc

A MEK tartalmára az OSZK felhasználási feltételei vonatkoznak. Ez a projekt nem hivatalos OSZK/MEK termék.
