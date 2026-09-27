# collector User-Agent を Chrome に変更

- 日付: 2026-08-14 07:35 JST
- 指示: UAはChromeじゃないの？
- 進捗: 達成

## 変更前

HTTP User-Agent と LyricFind `useragent` クエリは `RenCrowLyricsCatalog/1.0` だった。
このUAでは歌詞ページHTMLが `403 Forbidden` になった。

## 変更後

```
Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.7559.236 Safari/537.36
```

Cursor内蔵ブラウザのUAは `Cursor/... Chrome/144 ... Electron/...` だったため、Electron/Cursor識別子は付けず通常のChrome UAにした。

## 検証

- `go test` / `go vet` 成功。HTML取得テストは `Chrome/` を要求し、旧UAを拒否する
- charts API: Chrome UA で `200` / code=100
- 歌詞ページHTML: Chrome UA でも `202`（CloudFront challenge）。ld+jsonなし。本文は保存していない

したがって曲一覧は charts API、実ページのhashはブラウザ相当の完了応答が取れるまで使わない。
