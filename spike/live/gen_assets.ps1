# Gera os insumos do spike: fala pt-BR em PCM 16 kHz e a tela com texto em 1280 e 768 px.
# Uso: powershell -NoProfile -File spike/live/gen_assets.ps1
Add-Type -AssemblyName System.Speech
Add-Type -AssemblyName System.Drawing
$dir = $PSScriptRoot

# Fala: SAPI "Microsoft Maria" direto em WAV 16 kHz, 16 bits, mono.
$tts = New-Object System.Speech.Synthesis.SpeechSynthesizer
$tts.SelectVoice("Microsoft Maria Desktop")
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$tts.SetOutputToWaveFile("$dir\pergunta.wav", $fmt)
$tts.Speak("Oi. Leia para mim o número do pedido e o valor total que aparecem na tela.")
$tts.Dispose()

# Tela: fundo claro, texto de documento, 16:9.
$bmp = New-Object System.Drawing.Bitmap(1280, 720)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$g.Clear([System.Drawing.Color]::FromArgb(250, 250, 250))
$titulo = New-Object System.Drawing.Font("Segoe UI", 28, [System.Drawing.FontStyle]::Bold)
$corpo = New-Object System.Drawing.Font("Segoe UI", 16)
$preto = [System.Drawing.Brushes]::Black
$g.DrawString("Pedido de compra 4827-B", $titulo, $preto, 60, 50)
$linhas = @(
  "Cliente: Padaria Três Irmãos Ltda",
  "Data de entrega: sexta-feira, 02/10/2026",
  "Item 1: farinha de trigo, 40 sacos",
  "Item 2: fermento biológico, 12 caixas",
  "Valor total: R$ 1.350,90",
  "Observação: descarregar pela porta dos fundos"
)
$y = 150
foreach ($l in $linhas) { $g.DrawString($l, $corpo, $preto, 60, $y); $y += 48 }
$g.Dispose()

# JPEG qualidade 70, como o ADR 0028.
$codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
$ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
$ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]70)
$bmp.Save("$dir\tela_1280.jpg", $codec, $ep)
$peq = New-Object System.Drawing.Bitmap($bmp, 768, 432)
$peq.Save("$dir\tela_768.jpg", $codec, $ep)
$peq.Dispose(); $bmp.Dispose()
