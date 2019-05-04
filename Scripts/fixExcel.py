def utf_to_windows(file):
    import codecs
    from shutil import copyfile
    import os
    copyfile(file, file + ".tmp")

    try:
        BLOCKSIZE = 1048576  # or some other, desired size in bytes
        with codecs.open(file + ".tmp", "r", "windows-1255") as sourceFile:
            with codecs.open(file, "w", "ANSI") as targetFile:
                while True:
                    contents = sourceFile.read(BLOCKSIZE)
                    print(contents)
                    if not contents:
                        break
                    targetFile.write(contents)
    except Exception as e:
        print("ERROR:", e)
        copyfile(file + ".tmp", file)
    os.remove(file + ".tmp")


if __name__ == '__main__':
    utf_to_windows(r"E:\Dropbox\Project\Emotiv\Exports\data\iaps\000000000--2019-05-02--10-33-48.csv")
