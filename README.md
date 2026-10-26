# DichNhanh

App dịch màn hình offline cho Windows, chạy model Gemma 3 trên máy qua [Ollama](https://ollama.com). Không cần mạng, không gửi dữ liệu đi đâu.

- Quét một vùng màn hình (game, truyện, chat...), OCR rồi dịch sang tiếng Việt.
- Gõ tiếng Việt trong ô chat, bấm phím tắt là đổi sang ngôn ngữ đang nói chuyện (Anh, Nhật, Trung, Hàn...).

## Yêu cầu
- Windows 10/11 64-bit
- Card đồ họa khoảng 8GB VRAM trở lên (máy yếu hơn dùng `gemma3:4b`)
- Ổ cứng trống khoảng 10GB

## Cài đặt
1. Cài Ollama: `winget install Ollama.Ollama` (hoặc tải ở ollama.com)
2. Tải model: `ollama pull gemma3:12b`
3. Hoặc chạy `CaiDat.bat` để làm tự động hai bước trên.
4. (Tùy chọn) Đọc chữ Nhật/Hàn: chạy `CaiOCR_Nhat_Han_(Admin).ps1` bằng quyền admin.

## Chạy từ mã nguồn / build exe
```
pip install -r requirements.txt
python dichnhanh.py
pyinstaller --noconfirm --onefile --windowed --name DichNhanh --collect-submodules winsdk dichnhanh.py
```
File exe nằm trong thư mục `dist`.

## Phím tắt
- `Ctrl+Alt+Q`: chọn vùng màn hình để dịch (bản dịch tự tắt sau 15 giây, bấm để tắt sớm)
- `Ctrl+Alt+W`: bật/tắt tự quét lại vùng vừa chọn
- `Ctrl+Shift+T`: dịch chữ tiếng Việt đang gõ sang ngôn ngữ đích và dán đè

Chuột phải icon dưới khay để đổi ngôn ngữ, model, bật "Chế độ chơi game" (đỡ lag GPU). Cài đặt nằm ở `%APPDATA%\DichNhanh\config.json`.
