# -*- coding: utf-8 -*-

from __future__ import absolute_import, division

import os
import sys

from glob import glob
from os.path import (basename, dirname, expanduser, ismount, realpath, 
                     splitdrive)

MAJOR_DEVICE_IDS_IDE = (
    3, 22, 33, 34, 56, 57, 88, 89, 90, 91
)
MAJOR_DEVICE_IDS_SCSI = (
    8, 65, 66, 67, 68, 69, 70, 71, 128, 129, 130, 131, 132, 133, 134, 135
)


def _fullpath(path):
    return realpath(expanduser(path))


def _get_parent_device_id(device_id):
    major = os.major(device_id)
    minor = os.minor(device_id)

    # For some device types, a block entry does not exist for partitions.
    # The minor device ID of the "whole disk" entry is given by the upper N
    # bits of the partition minor device ID.
    #
    # Only SCSI and IDE devices are handled.
    #
    # https://www.kernel.org/doc/Documentation/admin-guide/devices.txt

    if major in MAJOR_DEVICE_IDS_IDE:
        disk_id = minor >> 6
        minor = disk_id * 64
    elif major in MAJOR_DEVICE_IDS_SCSI:
        # SCSI devices
        disk_id = minor >> 4
        minor = disk_id * 16

    device_id = "{0}:{1}".format(major, minor)
    return device_id


def _blkdevice(path):
    device_id = _get_parent_device_id(os.stat(_fullpath(path)).st_dev)
    block = ""

    for device in glob("/sys/class/block/*/dev"):
        if open(device).read().strip() == device_id:
            block = basename(dirname(device))

    return block


def is_nt_ssd(path):
    import win32file

    flag = False

    path = _fullpath(path)
    drive = splitdrive(path)[0].upper()

    drivetype = win32file.GetDriveType(drive)

    if drivetype == win32file.DRIVE_RAMDISK:
        flag = True

    elif drivetype in (win32file.DRIVE_FIXED, win32file.DRIVE_REMOVABLE):
        import wmi

        c = wmi.WMI()
        phy_to_part = 'Win32_DiskDriveToDiskPartition'
        log_to_part = 'Win32_LogicalDiskToPartition'
        index = dict((log_disk.Caption, phy_disk.Index)
                     for phy_disk in c.Win32_DiskDrive()
                     for partition in phy_disk.associators(phy_to_part)
                     for log_disk in partition.associators(log_to_part))

        c = wmi.WMI(moniker='//./ROOT/Microsoft/Windows/Storage')
        flag = bool(c.MSFT_PhysicalDisk(DeviceId=str(index[drive]),
                                        MediaType=4))

    return flag


def is_osx_ssd(path):
    import subprocess

    block = _blkdevice(path)
    cmd = 'diskutil info {0} | grep "Solid State"'.format(block)
    try:
        out = subprocess.check_output(cmd)
        flag = 'y' in out.lower()

    except subprocess.CalledProcessError:
        flag = False

    return flag


def is_posix_ssd(path):
    block = _blkdevice(path)
    path = '/sys/block/{0}/queue/rotational'.format(block)
    try:
        with open(path) as fp:
            flag = fp.read().strip() == "0"

    except (IOError, OSError):
        flag = False

    return flag


def is_ssd(path):
    if os.name == 'nt':
        _is_ssd = is_nt_ssd
    elif sys.platform == 'darwin':
        _is_ssd = is_osx_ssd
    else:
        _is_ssd = is_posix_ssd

    return _is_ssd(path)
