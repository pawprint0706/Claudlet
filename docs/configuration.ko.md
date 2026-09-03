# 설정

[← README](../README.ko.md) · [English](configuration.md) | **한국어**

어떤 코딩 에이전트 활동에 어떤 애니메이션을 보일지 `~/.config/claudlet/config.json`에서
재매핑해요 (모든 키 선택).

> **팁:** `claudlet-config`(또는 Claude에게 `/claudlet config`) 실행하면 정확한 경로,
> 현재 적용값, 그리고 오타·잘못된 슬롯 때문에 **조용히 버려진 항목**까지 보여줘요.
> `claudlet-config init`은 시작 템플릿 생성, `claudlet-config open`은 에디터로 열기.

예시:

```json
{
  "tools":      { "Bash": "work_search", "Grep": "sing", "*": "work_computer" },
  "events":     { "prompt": "thinking", "celebrate": "juggle" },
  "raw_events": { "PostToolUse": "celebrate", "SubagentStop": "wave" }
}
```

- **`tools`** — 도구명 → 상태. `"*"`는 매핑 안 된 도구의 폴백. `mcp__*`는 명시 안 하면
  `work_web`.
- **`events`** — 이벤트 슬롯 → 상태. 슬롯: `start`, `prompt`, `done`, `celebrate`, `error`,
  `permission`, `idle_prompt`.
- **`raw_events`** — 슬롯 없는 원본 훅 이벤트명 → 상태 (`PostToolUse`, `SubagentStop`,
  `PreCompact` 등). 훅이 보내는 이벤트명만 알면 매핑 가능. 슬롯 있는 이벤트는 기본 동작 유지.

값은 알려진 상태/모션이어야 해요:

```
work_computer  work_search  work_web  work_agent  work_skill
idle  sleeping  thinking  attention  asking  error  celebrate
jump  wave  sing  juggle
```

모르는 값은 무시돼 기본값으로 폴백하니, 오타가 나도 안전해요. 바꾸면 펫 재시작.

## 언어

`lang`은 펫의 말풍선·트레이 툴팁·우클릭 메뉴 언어를 정해요 — `"ko"`, `"en"`, 또는
`"auto"`(기본값; 로케일 따라가고, 안 되면 영어):

```json
{ "lang": "en" }
```

## 팔레트

`palette`는 전체 기본 팔레트를 정하고, `palettes`는 펫을 시작한 코딩 에이전트별로
그 값을 덮어써요:

```json
{
  "palette": "auto",
  "palettes": { "codex": "shiny_violet", "claude": "default" }
}
```

팔레트 값은 `auto`, `default`, `shiny_teal`, `shiny_violet`입니다.
펫이 어느 에이전트 소속인지는 세션 환경 변수(`CODEX_THREAD_ID`/`CODEX_SESSION_ID` vs
`CLAUDE_CODE_SESSION_ID`)로 감지하고, 없으면 띄운 프로세스 이름으로 판단해요.
`CLAUDLET_PALETTE` 환경 변수는 한 프로세스에 한해 가장 높은 우선순위로 적용되고,
`CLAUDLET_AGENT=claude|codex`로 에이전트 종류를 강제할 수 있어요.

## 위치 (도크)

펫은 기본적으로 모니터 **오른쪽 아래 구석**에 고정돼서 서요. 여러 마리를 띄우면
겹치지 않고 **옆으로 나란히** 서고(오른쪽 → 왼쪽), 한 줄이 화면 폭을 넘으면 다음 줄로
접혀요. 앞에 선 펫이 종료하면 뒷펫이 자동으로 당겨 서서 대열이 다시 촘촘해져요.

**마우스로 끌어서 옮길 수 있어요.** 한 마리를 끌면 대열 전체가 간격을 유지한 채 따라오고,
그 자리는 config에 저장돼서 다음에 뜨는 펫도 같은 곳에 서요. 우클릭 메뉴의
**"제자리로"**로 원래 구석으로 되돌릴 수 있어요.

```json
{
  "dock": {
    "enabled": true,
    "anchor": "bottom-right",
    "screen": "primary",
    "gap": 4,
    "offset": { "x": 0, "y": 0 }
  }
}
```

- **`enabled`** — `false`면 예전처럼 데스크톱을 배회해요(중력·창 걸터앉기 부활).
  우클릭 메뉴의 **"자유롭게 돌아다니기"**와 같은 스위치이고, 거기서 바꾼 값도 여기 저장돼요.
- **`anchor`** — `bottom-right`(기본) · `bottom-left` · `top-right` · `top-left`.
  대열은 앵커의 반대 방향으로 자라요.
- **`screen`** — `"primary"`(기본) 또는 모니터 인덱스 정수(`0`, `1`, …). 범위를 벗어나면
  주 모니터로 폴백해요. 어느 인덱스가 어느 모니터인지 굳이 찾지 말고, 그냥 원하는
  모니터로 펫을 **끌어다 놓는 게 더 빨라요** — 그 위치가 그대로 기억되니까요.
- **`gap`** — 펫 사이 간격(px).
- **`offset`** — 앵커로부터의 변위. 드래그하면 여기 자동으로 기록되니 손으로 적을 일은
  거의 없어요.

> `roam_area` / `no_go`(금지구역)는 **배회 중일 때만** 적용돼요. 도크 중인 펫은 좌표가
> 사용자가 정한 자리라서 그 제한을 받지 않아요.
