# Google Tasks MCP — Bắt đầu nhanh

**Public beta · mục tiêu phát hành v0.4.0**

`v0.4.0` là mục tiêu phát hành hiện tại. Trước khi cài, xác nhận
[GitHub Release `v0.4.0`](https://github.com/phamviet86/google-task-mcp/releases/tag/v0.4.0) đã có
wheel, source archive và `SHA256SUMS`. Trước thời điểm đó, không coi source branch hoặc tag là bản
đã phát hành. Bản `v0.4.0` có `google-tasks-mcp install-skills` và `google-tasks-mcp doctor` cho
luồng onboarding bằng agent; wheel `v0.3.1` đã phát hành không có hai lệnh này. Xem [hướng dẫn
agent-led](docs/agent-setup.md).

`google-task-mcp` là kho mã nguồn. Lệnh MCP là `google-tasks-mcp` và
`google-tasks-mcp-auth`. Tên gói Python dành cho dự án này là
`phamviet-google-tasks-mcp`; **không** cài `google-tasks-mcp` từ PyPI vì đó là gói không liên quan.

Sau khi xác nhận release assets, không cần clone mã nguồn. Máy macOS hoặc Linux cần
[`uv`](https://docs.astral.sh/uv/getting-started/installation/); nếu `uv --version` không chạy,
hãy cài `uv` theo hướng dẫn chính thức và mở terminal mới. Các lệnh dưới đây để `uv` cài Python 3.12
và dùng thư mục versioned mà người dùng có quyền ghi:

```bash
uv --version
uv python install 3.12
INSTALL_ROOT="$HOME/.local/share/google-tasks-mcp/v0.4.0"
mkdir -p "$INSTALL_ROOT"
```

Tải wheel và `SHA256SUMS`, kiểm tra checksum, rồi cài chính file wheel local đã được kiểm tra:

```bash
INSTALL_ROOT="$HOME/.local/share/google-tasks-mcp/v0.4.0"
DOWNLOAD_DIR="$INSTALL_ROOT/downloads"
WHEEL_NAME="phamviet_google_tasks_mcp-0.4.0-py3-none-any.whl"
mkdir -p "$DOWNLOAD_DIR"
curl -fL -o "$DOWNLOAD_DIR/$WHEEL_NAME" \
  "https://github.com/phamviet86/google-task-mcp/releases/download/v0.4.0/$WHEEL_NAME"
curl -fL -o "$DOWNLOAD_DIR/SHA256SUMS" \
  "https://github.com/phamviet86/google-task-mcp/releases/download/v0.4.0/SHA256SUMS"
(cd "$DOWNLOAD_DIR" && shasum -a 256 -c SHA256SUMS --ignore-missing)
uv venv --python 3.12 "$INSTALL_ROOT/venv"
uv pip install --python "$INSTALL_ROOT/venv/bin/python" "$DOWNLOAD_DIR/$WHEEL_NAME"
"$INSTALL_ROOT/venv/bin/google-tasks-mcp-auth" --version
```

Trên Linux, dùng `sha256sum -c SHA256SUMS --ignore-missing`. PyPI chưa phát hành gói này; chỉ dùng
wheel từ GitHub Release. Server đã cài ở
`$HOME/.local/share/google-tasks-mcp/v0.4.0/venv/bin/google-tasks-mcp`. File cấu hình MCP không tự
mở rộng `$HOME`, vì vậy cần thay bằng đường dẫn home tuyệt đối của máy khi cấu hình client.

Tiếp theo, agent cài các skill đóng gói, đọc `google-tasks-setup` đã cài, dùng
`references/runtime.json` của skill để chạy `doctor`, hướng dẫn OAuth, cấu hình client bằng đường
dẫn server tuyệt đối, rồi dùng skill `google-tasks`:

```bash
"$INSTALL_ROOT/venv/bin/google-tasks-mcp" install-skills
```

Trong Google Cloud, bật **Google Tasks API**, tạo OAuth client loại **Desktop app**, và lưu file JSON
ngoài kho mã. Xác thực trên máy chạy MCP:

```bash
INSTALL_ROOT="$HOME/.local/share/google-tasks-mcp/v0.4.0"
GOOGLE_TOKEN_FILE="$HOME/.config/google-tasks-mcp/token.json" \
  "$INSTALL_ROOT/venv/bin/google-tasks-mcp-auth" \
  --client-secret "$HOME/.config/google-tasks-mcp/client_secret.json"
```

Sau đó cấu hình MCP client bằng đường dẫn tuyệt đối như
`/duong-dan-home-tuyet-doi/.local/share/google-tasks-mcp/v0.4.0/venv/bin/google-tasks-mcp`, và
truyền cùng giá trị `GOOGLE_TOKEN_FILE`. Không chạy `uv run` cho bản cài từ release; lệnh đó chỉ dùng
trong source checkout khi phát triển.

Khi làm theo console hiện tại, xem [Google Tasks Python quickstart](https://developers.google.com/workspace/tasks/quickstart/python).
Chọn audience của OAuth consent screen phù hợp với account và project đã chọn; không tự mặc định là
Internal. Tham khảo [hướng dẫn token hết hạn OAuth](https://developers.google.com/identity/protocols/oauth2#expiration)
khi cần xác thực lại.

Server vẫn chỉ dùng stdio và không mở network port. Authorization helper có thể dùng callback
loopback local tạm thời khi người dùng hoàn tất luồng OAuth trên trình duyệt.

Máy chủ chỉ dùng `stdio`, không mở cổng mạng, không có cơ sở dữ liệu hoặc tiến trình nền. Có thể khởi
tạo MCP và xem 14 tools khi chưa xác thực; lần gọi tool đầu tiên sẽ báo lỗi xác thực cho đến khi tạo
token. macOS và Linux được hỗ trợ cho `v0.4.0`; Windows chưa được kiểm chứng.

Trong `v0.4.0`, `install-skills` cài hai skill đóng gói và tạo `references/runtime.json` không chứa
bí mật, gồm identifier `distribution`/`version` và đường dẫn tuyệt đối `python`, `server`, `auth`.
`doctor` chỉ kiểm tra metadata/permission của đường dẫn token; `authentication` và
`mcp_discovery` vẫn là `unverified`, nên token hiện diện hoặc xem được tools không chứng minh đã
đăng nhập Google. Chỉ thực hiện một lần `list_task_lists` read-only khi người dùng đã cho phép kiểm
tra live hoặc yêu cầu rõ ràng cấu hình và xác minh cho sử dụng.

Kết quả thành công của list tool là JSON có mảng `task_lists` hoặc `tasks` và
`next_page_token`; delete/clear trả acknowledgement JSON. Khi MCP trả lỗi (`isError: true`), text
là thông báo lỗi, không phải JSON result. Agent cần đọc lại target trước khi thử lại write bị lỗi và
luôn xin xác nhận trước delete/clear.

Xem hướng dẫn đầy đủ bằng tiếng Anh, gồm Codex/Hermes config, troubleshooting, rollback và các JSON
mẫu: [README.md](README.md) và [triển khai/phát hành](docs/release-deployment.md).
