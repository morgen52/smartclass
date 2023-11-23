import os


def clear():
    # dirs = ["pic", "audio", "text"]

    # for dir in dirs:
    #     for file in os.listdir(dir):
    #         path = os.path.join(dir, file)
    #         os.remove(path)

    if not os.path.exists("old"):
        os.mkdir("old")
    os.system("rm -rf ./old/*")

    dirs = ["pic", "audio", "text", "log"]
    for dir in dirs:
        if os.path.exists(dir):
            os.system(f"mv {dir} ./old/")
        os.mkdir(dir)
    
    # save database
    os.system("cp ./database.db ./old/")
        
    
