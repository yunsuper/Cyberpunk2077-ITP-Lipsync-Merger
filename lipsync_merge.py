#!/usr/bin/env python3
"""
ITP Lipsync Merger
Immersive Third Person V2의 영어 전용 V 립싱크를 다른 음성 언어(.lipmap)에 병합해
해당 언어용 아카이브를 사용자 PC에서 직접 만든다.

원본 모드 데이터와 게임 파일은 이 저장소에 포함되지 않는다.
사용자가 이미 설치한 원본 모드 아카이브와 게임의 언어별 .lipmap을 입력으로 쓴다.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

V_VOICE_TAG = "1103967280742240864"  # V의 목소리 태그


def run_wk(wk, *args):
    """WolvenKit CLI 실행. 실패하면 출력과 함께 종료."""
    cmd = [wk, *args]
    print("  $", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        sys.exit(f"WolvenKit CLI 실행 실패: {' '.join(args[:1])}")
    return r.stdout


def cname(v):
    return v.get("$value") if isinstance(v, dict) else v


def index_files(root):
    """추출 폴더의 파일을 '소문자 게임 경로(\\ 구분)' → 실제 경로로 매핑."""
    m = {}
    for d, _, files in os.walk(root):
        for f in files:
            full = os.path.join(d, f)
            rel = os.path.relpath(full, root).replace(os.sep, "\\").lower()
            m[rel] = full
    return m


def merge(src, dst, mod_paths, src_lang, dst_lang):
    """
    src: 원본 모드의 lipmap RootChunk (예: en-us)
    dst: 대상 언어의 게임 원본 lipmap RootChunk (예: kr-kr) - 제자리 수정
    mod_paths: 모드 아카이브 안 파일 경로(소문자) 집합
    반환: (통계 dict, [(원본 anims 경로, 대상 anims 경로)])
    """
    src_seg = f"\\{src_lang}\\"
    dst_seg = f"\\{dst_lang}\\"
    didx = {s: i for i, s in enumerate(dst["scenePaths"])}
    stats = {"added": 0, "kept": 0, "new_scenes": 0}
    copies = set()
    new_rows = []

    for scene, preview, entry in zip(src["scenePaths"], src["scenePreviewPaths"], src["sceneEntries"]):
        # 모드가 추가한 V 항목만 사용 (게임 원본 V 항목은 대상 언어 원본을 따름)
        vpaths = [
            a["DepotPath"]["$value"]
            for t, a in zip(entry["actorVoiceTags"], entry["animSets"])
            if t == V_VOICE_TAG and a["DepotPath"]["$value"].lower() in mod_paths
        ]
        if not vpaths:
            continue
        vp = vpaths[0]
        if src_seg not in vp:
            sys.exit(f"예상한 언어 경로({src_seg})가 없음: {vp}")
        tp = vp.replace(src_seg, dst_seg, 1)
        anim = {"DepotPath": {"$type": "ResourcePath", "$storage": "string", "$value": tp}, "Flags": "Soft"}

        if scene in didx:
            de = dst["sceneEntries"][didx[scene]]
            if V_VOICE_TAG in de["actorVoiceTags"]:
                stats["kept"] += 1  # 대상 언어 음성에 맞춘 원본 V 립싱크 유지
                continue
            de["actorVoiceTags"].append(V_VOICE_TAG)
            de["animSets"].append(anim)
            stats["added"] += 1
        else:
            new_rows.append((int(scene), scene, preview, {
                "$type": "animLipsyncMappingSceneEntry",
                "actorVoiceTags": [V_VOICE_TAG],
                "animSets": [anim],
            }))
            stats["new_scenes"] += 1
        copies.add((vp, tp))

    # 새 장면은 scenePaths 숫자 오름차순을 유지하며 삽입
    if new_rows:
        rows = list(zip([int(x) for x in dst["scenePaths"]], dst["scenePaths"],
                        dst["scenePreviewPaths"], dst["sceneEntries"]))
        rows += new_rows
        rows.sort(key=lambda r: r[0])
        dst["scenePaths"] = [r[1] for r in rows]
        dst["scenePreviewPaths"] = [r[2] for r in rows]
        dst["sceneEntries"] = [r[3] for r in rows]

    stats["anims"] = len(copies)
    stats["scenes_total"] = len(dst["sceneEntries"])
    stats["v_entries_total"] = sum(1 for e in dst["sceneEntries"] for t in e["actorVoiceTags"] if t == V_VOICE_TAG)
    return stats, sorted(copies)


def main():
    p = argparse.ArgumentParser(description="ITP V2 V 립싱크를 다른 음성 언어용 아카이브로 병합")
    p.add_argument("--wolvenkit", required=True, help="WolvenKit CLI 실행 파일 경로 (WolvenKit.CLI.exe 등)")
    p.add_argument("--mod-archive", required=True, help="원본 모드의 immersive_third_person_v_lipsync_en.archive")
    p.add_argument("--target-lipmap", required=True, help="게임에서 추출한 대상 언어 .lipmap (예: kr-kr.lipmap)")
    p.add_argument("--out", default="output", help="결과 아카이브를 저장할 폴더 (기본: output)")
    p.add_argument("--keep-work", action="store_true", help="작업 폴더를 지우지 않음 (디버그용)")
    a = p.parse_args()

    for f in (a.wolvenkit, a.mod_archive, a.target_lipmap):
        if not os.path.isfile(f):
            sys.exit(f"파일을 찾을 수 없음: {f}")

    work = tempfile.mkdtemp(prefix="itp_lipsync_")
    try:
        ext, js, build, pack, verify = (os.path.join(work, d) for d in ("ext", "json", "build", "pack", "verify"))
        for d in (ext, js, build, pack, verify):
            os.makedirs(d)

        print("[1/6] 원본 모드 아카이브 추출")
        run_wk(a.wolvenkit, "extract", a.mod_archive, "-o", ext)
        files = index_files(ext)
        src_lipmap = next((v for k, v in files.items() if k.startswith("base\\localization\\") and k.endswith(".lipmap")), None)
        if not src_lipmap:
            sys.exit("모드 아카이브에서 .lipmap을 찾지 못함")

        print("[2/6] .lipmap → JSON 변환")
        run_wk(a.wolvenkit, "convert", "s", src_lipmap, "-o", js)
        tgt_copy = os.path.join(work, os.path.basename(a.target_lipmap))
        shutil.copy2(a.target_lipmap, tgt_copy)
        run_wk(a.wolvenkit, "convert", "s", tgt_copy, "-o", js)
        src_json = os.path.join(js, os.path.basename(src_lipmap) + ".json")
        tgt_json = os.path.join(js, os.path.basename(tgt_copy) + ".json")

        print("[3/6] 변환 신뢰성 확인 (대상 lipmap 왕복 변환)")
        rt = os.path.join(work, "roundtrip")
        os.makedirs(rt)
        run_wk(a.wolvenkit, "convert", "d", tgt_json, "-o", rt)
        with open(os.path.join(rt, os.path.basename(tgt_copy)), "rb") as x, open(tgt_copy, "rb") as y:
            if x.read() != y.read():
                sys.exit("왕복 변환 결과가 원본과 다름. 이 WolvenKit 버전으로는 안전하게 진행할 수 없음")
        print("  왕복 변환 바이트 동일")

        print("[4/6] V 립싱크 병합")
        src_doc = json.load(open(src_json, encoding="utf-8"))
        tgt_doc = json.load(open(tgt_json, encoding="utf-8"))
        src, dst = src_doc["Data"]["RootChunk"], tgt_doc["Data"]["RootChunk"]
        src_lang, dst_lang = cname(src["languageCodeName"]), cname(dst["languageCodeName"])
        if src_lang == dst_lang:
            sys.exit(f"원본과 대상 언어가 같음: {src_lang}")
        stats, copies = merge(src, dst, set(files), src_lang, dst_lang)
        print(f"  {src_lang} → {dst_lang}")
        print(f"  기존 장면에 V 추가 {stats['added']} / 대상 원본 V 유지 {stats['kept']} / 새 장면 {stats['new_scenes']}")
        print(f"  복사할 v.anims {stats['anims']} / 결과 장면 {stats['scenes_total']}, V 항목 {stats['v_entries_total']}")

        print("[5/6] 결과 lipmap 생성 및 애니메이션 복사")
        loc = os.path.join(build, "archive", "base", "localization")
        os.makedirs(loc)
        merged_json = os.path.join(work, os.path.basename(tgt_copy) + ".json")
        json.dump(tgt_doc, open(merged_json, "w", encoding="utf-8"), ensure_ascii=False)
        run_wk(a.wolvenkit, "convert", "d", merged_json, "-o", loc)
        for vp, tp in copies:
            src_file = files.get(vp.lower())
            if not src_file:
                sys.exit(f"모드 아카이브에 없는 파일: {vp}")
            dst_file = os.path.join(build, "archive", *tp.split("\\"))
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            shutil.copy2(src_file, dst_file)

        print("[6/6] 패킹 및 검증")
        run_wk(a.wolvenkit, "pack", os.path.join(build, "archive"), "-o", pack)
        packed = next((os.path.join(pack, f) for f in os.listdir(pack) if f.endswith(".archive")), None)
        if not packed:
            sys.exit("패킹 결과 아카이브가 없음")
        run_wk(a.wolvenkit, "extract", packed, "-o", verify)
        want, got = index_files(os.path.join(build, "archive")), index_files(verify)
        if set(want) != set(got):
            sys.exit("패킹 결과 파일 목록이 다름")
        for k in want:
            with open(want[k], "rb") as x, open(got[k], "rb") as y:
                if x.read() != y.read():
                    sys.exit(f"패킹 결과 내용이 다름: {k}")
        print(f"  재추출 {len(want)}개 파일 전부 일치")

        out_dir = os.path.join(a.out, "archive", "pc", "mod")
        os.makedirs(out_dir, exist_ok=True)
        final = os.path.join(out_dir, f"immersive_third_person_v_lipsync_{dst_lang}.archive")
        shutil.move(packed, final)
        print(f"\n완료: {final}")
    finally:
        if a.keep_work:
            print(f"작업 폴더 유지: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
