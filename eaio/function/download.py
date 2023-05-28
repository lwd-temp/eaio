import json
import io
import zipfile
from pathlib import Path

import requests
from loguru import logger


from eaio import __electron_source__, __electron_repo_root__, __electron_repo__, __platform__
from eaio.util.error import DownloadError


def download_electron(drive: Path, version: str, arch: str, proxy: str | None = None, source: str = __electron_source__[0]):
    """
    在指定磁盘分区下载指定指定版本、平台、架构的 Electron，可选指定代理和在线仓库源
    :param drive: 磁盘分区, 形如 C:/
    :param version: 版本
    :param arch: 架构
    :param proxy: 代理，可选
    :param source: 仓库源，可选
    :return:
    :raise: DownloadError
    """
    repo = drive.joinpath(__electron_repo_root__).joinpath(__electron_repo__.format(version=version, arch=arch))
    if repo.exists() and not repo.is_dir():
        logger.warning(f"{repo} 存在但不是文件夹, 自动删除")
        repo.unlink()
    if not repo.exists():
        logger.info(f"{repo} 不存在, 自动创建")
        repo.mkdir(parents=True)

    logger.info("正在下载 Electron 预编译程序")
    logger.debug(f"目标链接仓库: {repo}")

    electron_url = source.format(version=version, platform=__platform__, arch=arch)
    logger.debug(f"下载地址: {electron_url}")

    signed_file = repo.joinpath('eaio.signed.json')
    if signed_file.exists():
        logger.info(f"{signed_file} 存在, 自动删除")
        signed_file.unlink()  # 删除校验文件，等价于将此目录标记为未下载完成/下载失败

    electron_resp = requests.get(electron_url, proxies={
        'http': proxy,
        'https': proxy,
    } if proxy else None)
    if electron_resp.status_code != 200:
        raise DownloadError(f"下载失败，HTTP {electron_resp.status_code}")

    signed = {}
    with io.BytesIO(electron_resp.content) as f:
        with zipfile.ZipFile(f, 'r') as zipf:
            for file in zipf.filelist:
                filename = repo.joinpath(file.filename)
                if filename.parent != repo:
                    if not filename.parent.exists():
                        filename.parent.mkdir(parents=True)
                with open(filename, 'wb') as rf:
                    # 通过覆写文件的方式来更新已被硬链接的应用，如果直接替换文件会导致已有的硬链接失效
                    rf.write(zipf.read(file.filename))
                signed[file.filename] = hex(file.CRC)
    with open(signed_file, 'w') as f:  # 写入校验文件，等价于将此目录标记为下载完成
        f.write(json.dumps(signed))
    logger.info("下载 Electron 预编译程序完成")