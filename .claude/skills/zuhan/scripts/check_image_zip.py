#!/usr/bin/env python3
"""ChatGPTから受け取った教材図版ZIPを安全に検査し、必要なら展開する。"""

from __future__ import annotations

import argparse
import binascii
import re
import struct
import sys
import zipfile
import zlib
from pathlib import Path, PurePosixPath


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ID_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.png")
MAX_MEMBERS = 1000
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_TOTAL_SIZE = 500 * 1024 * 1024


class ValidationError(Exception):
    """利用者が修正できるZIP検査エラー。"""


def validate_png(data: bytes, expected_width: int | None, expected_height: int | None) -> None:
    """PNGのチャンク、CRC、寸法、終端を検査する。"""
    if not data.startswith(PNG_SIGNATURE):
        raise ValidationError("PNG署名が不正")

    offset = len(PNG_SIGNATURE)
    seen_ihdr = False
    seen_idat = False
    seen_iend = False
    width = height = None
    while offset < len(data):
        if len(data) - offset < 12:
            raise ValidationError("PNGチャンクが途中で切れている")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise ValidationError("PNGチャンク長がファイル範囲を超えている")
        chunk_data = data[offset + 8 : offset + 8 + length]
        stored_crc = struct.unpack(">I", data[offset + 8 + length : end])[0]
        actual_crc = zlib.crc32(chunk_type)
        actual_crc = zlib.crc32(chunk_data, actual_crc) & 0xFFFFFFFF
        if stored_crc != actual_crc:
            name = chunk_type.decode("ascii", errors="replace")
            raise ValidationError(f"PNGチャンク {name} のCRCが不正")

        if not seen_ihdr:
            if chunk_type != b"IHDR" or length != 13:
                raise ValidationError("先頭チャンクが正しいIHDRではない")
            width, height = struct.unpack(">II", chunk_data[:8])
            if width == 0 or height == 0:
                raise ValidationError("PNG寸法が0")
            bit_depth, color_type, compression, filtering, interlace = chunk_data[8:]
            valid_depths = {
                0: {1, 2, 4, 8, 16},
                2: {8, 16},
                3: {1, 2, 4, 8},
                4: {8, 16},
                6: {8, 16},
            }
            if color_type not in valid_depths or bit_depth not in valid_depths[color_type]:
                raise ValidationError(
                    f"IHDRのbit depth/color typeが不正: {bit_depth}/{color_type}"
                )
            if compression != 0 or filtering != 0 or interlace not in {0, 1}:
                raise ValidationError("IHDRの圧縮・フィルター・インターレース方式が不正")
            seen_ihdr = True
        elif chunk_type == b"IHDR":
            raise ValidationError("IHDRが重複している")
        elif chunk_type == b"IDAT":
            seen_idat = True

        offset = end
        if chunk_type == b"IEND":
            if length != 0:
                raise ValidationError("IENDチャンク長が不正")
            seen_iend = True
            break

    if not seen_ihdr or not seen_idat or not seen_iend:
        raise ValidationError("IHDR、IDAT、IENDのいずれかがない")
    if offset != len(data):
        raise ValidationError("IEND後に余分なデータがある")
    if expected_width is not None and width != expected_width:
        raise ValidationError(f"幅 {width}px（期待値 {expected_width}px）")
    if expected_height is not None and height != expected_height:
        raise ValidationError(f"高さ {height}px（期待値 {expected_height}px）")


def validate_args(args: argparse.Namespace) -> tuple[str, ...]:
    if not ID_RE.fullmatch(args.id):
        raise ValidationError("--id は小文字英数字とハイフンだけで指定する")
    if not args.expect:
        raise ValidationError("--expect を1個以上指定する")
    if len(args.expect) != len(set(args.expect)):
        raise ValidationError("--expect に重複がある")
    for name in args.expect:
        if not NAME_RE.fullmatch(name) or PurePosixPath(name).name != name:
            raise ValidationError(
                f"不正な --expect: {name!r}（ディレクトリを含まないPNG名にする）"
            )
    if (args.width is None) != (args.height is None):
        raise ValidationError("--width と --height は両方指定するか、両方省略する")
    if args.width is not None and (args.width <= 0 or args.height <= 0):
        raise ValidationError("寸法は正の整数にする")
    return tuple(f"{args.id}/{name}" for name in args.expect)


def is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return (mode & 0o170000) == 0o120000


def inspect_archive(
    archive_path: Path,
    expected_paths: tuple[str, ...],
    expected_width: int | None,
    expected_height: int | None,
) -> dict[str, bytes]:
    """ZIPを検査し、検証済みPNGのバイト列を内部パス別に返す。"""
    if not archive_path.is_file():
        raise ValidationError(f"ZIPが見つからない: {archive_path}")

    try:
        archive = zipfile.ZipFile(archive_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValidationError(f"ZIPを開けない: {exc}") from exc

    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBERS:
            raise ValidationError(f"ZIP内項目数が上限 {MAX_MEMBERS} を超える")
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            duplicates = sorted({name for name in names if names.count(name) > 1})
            raise ValidationError("ZIP内パスが重複: " + ", ".join(duplicates))

        allowed_directory = expected_paths[0].split("/", 1)[0] + "/"
        file_infos: dict[str, zipfile.ZipInfo] = {}
        for info in infos:
            name = info.filename
            path = PurePosixPath(name)
            if "\\" in name or name.startswith("/") or ".." in path.parts:
                raise ValidationError(f"危険なZIP内パス: {name!r}")
            if info.is_dir():
                if name != allowed_directory:
                    raise ValidationError(f"想定外のディレクトリ: {name}")
                continue
            if is_symlink(info):
                raise ValidationError(f"シンボリックリンクは禁止: {name}")
            if info.flag_bits & 0x1:
                raise ValidationError(f"暗号化ファイルは禁止: {name}")
            file_infos[name] = info

        actual = set(file_infos)
        expected = set(expected_paths)
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        problems = []
        if missing:
            problems.append("不足: " + ", ".join(missing))
        if extra:
            problems.append("想定外: " + ", ".join(extra))
        if problems:
            raise ValidationError(" / ".join(problems))

        total_size = sum(info.file_size for info in file_infos.values())
        if total_size > MAX_TOTAL_SIZE:
            raise ValidationError(
                f"展開後合計が上限 {MAX_TOTAL_SIZE // (1024 * 1024)}MiB を超える"
            )

        checked: dict[str, bytes] = {}
        for path in expected_paths:
            info = file_infos[path]
            if info.file_size > MAX_FILE_SIZE:
                raise ValidationError(
                    f"{path}: 上限 {MAX_FILE_SIZE // (1024 * 1024)}MiB を超える"
                )
            try:
                data = archive.read(info)
            except (OSError, RuntimeError, zipfile.BadZipFile, binascii.Error) as exc:
                raise ValidationError(f"{path}: ZIPデータを読めない: {exc}") from exc
            try:
                validate_png(data, expected_width, expected_height)
            except ValidationError as exc:
                raise ValidationError(f"{path}: {exc}") from exc
            checked[path] = data
        return checked


def extract_checked(files: dict[str, bytes], destination: Path) -> None:
    """検証済みファイルだけを、新しいディレクトリへ展開する。"""
    if destination.exists() or destination.is_symlink():
        raise ValidationError(f"展開先は存在しない新規パスにする: {destination}")
    destination.mkdir(parents=True)
    targets = {name: destination.joinpath(*PurePosixPath(name).parts) for name in files}
    for name, data in files.items():
        target = targets[name]
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(data)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="検査するZIP")
    parser.add_argument("--id", required=True, help="教材ID")
    parser.add_argument(
        "--expect", action="append", default=[], metavar="FILE.png", help="期待するPNG名"
    )
    parser.add_argument("--width", type=int, help="期待する幅")
    parser.add_argument("--height", type=int, help="期待する高さ")
    parser.add_argument("--extract-to", type=Path, help="検査合格後の展開先")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        expected_paths = validate_args(args)
        files = inspect_archive(args.archive, expected_paths, args.width, args.height)
        if args.extract_to is not None:
            extract_checked(files, args.extract_to)
    except ValidationError as exc:
        print(f"不合格: {exc}", file=sys.stderr)
        return 1

    size = "寸法は未指定"
    if args.width is not None:
        size = f"{args.width}x{args.height}px"
    message = f"合格: {len(files)}個のPNG、内部パス・CRC・PNG構造・{size}を確認"
    if args.extract_to is not None:
        message += f"、{args.extract_to} へ展開"
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
