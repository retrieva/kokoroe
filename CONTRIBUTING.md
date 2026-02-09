# Contributing Guide / コントリビューションガイド

このプロジェクトへの貢献ありがとうございます 🎉
本ドキュメントでは、開発に参加する際の基本的なルールやフローをまとめています。

---

## 開発フロー

* `main` ブランチは **常にデプロイ可能な状態** を保ちます
* `dev` ブランチを開発用のメインブランチとします
* 作業内容ごとに `feature/xxx` などのブランチを `dev` から作成します
* 開発完了後は Pull Request（PR）を作成し、レビューを経て `dev` にマージします
* リリース時に `dev` から `main` へマージします

> いわゆる **git-flow** をベースとした運用です

---

## ブランチルール

用途に応じて、以下の命名規則を使用してください。

* `feature/xxx` : 新機能の追加
* `fix/xxx`     : バグ修正
* `docs/xxx`    : ドキュメントの更新

`xxx` には、作業内容が分かる簡潔な名前を付けてください。

---

## コミットメッセージ

* 1行目に **変更内容を要約** してください

  * 例：`投稿フォームの作成`
* 追加の説明が必要な場合は、空行を挟んで本文に詳細を記載します

例：

```
投稿フォームの作成

- バリデーションを追加
- デザインを調整
```

---

## Pull Request 作成手順

1. 作業ブランチから `dev` ブランチに向けて PR を作成します
2. タイトルは **日本語・英語いずれでも可** ですが、内容が明確に分かるように記載してください
3. PR テンプレートが用意されている場合は、必ず使用してください
4. CI がすべて通過していることを確認してください
5. レビューでの指摘に対応後、承認を得てマージします

---

## Language / 言語について

* PR・コミットメッセージ・ブランチ名は **英語・日本語どちらでも可** とします
* プログラム内（コード・変数名・関数名など）の言語は **英語を推奨** します

  * 日本語の使用も問題ありません

---

---

# Contributing Guide (English)

Thank you for contributing to this project 🎉
This document describes the basic rules and development flow for contributors.

---

## Development Flow

* The `main` branch must always be kept **deployable**
* The `dev` branch is used as the main development branch
* Create working branches such as `feature/xxx` from `dev`
* After completing development, open a Pull Request (PR) and merge it into `dev` after review
* When releasing, merge `dev` into `main`

> This project follows a **git-flow–based** workflow

---

## Branch Rules

Please follow the naming conventions below depending on the purpose:

* `feature/xxx` : New features
* `fix/xxx`     : Bug fixes
* `docs/xxx`    : Documentation updates

Use a short and descriptive name for `xxx`.

---

## Commit Messages

* Summarize the change in the **first line**

  * Example: `Create post form`
* Add additional details in the body if necessary, separated by a blank line

Example:

```
Create post form

- Add validation
- Adjust design
```

---

## Pull Request Process

1. Create a PR from your working branch to the `dev` branch
2. The title can be written in **Japanese or English**, but must be clear and descriptive
3. Use the PR template if one is provided
4. Make sure all CI checks are passing
5. Address review comments and merge after approval

---

## Language

* Japanese and English are both acceptable for PRs, commit messages, and branch names
* English is **preferred** for code (variables, functions, etc.)

  * Japanese may be used when appropriate

---

If you have any questions or suggestions, feel free to open an Issue or Pull Request 👍

