from  rag_kmk import CONFIG

def main():
    '''
        This is the sample function to run the RAG-KMK
    '''       
    print("CONFIG:",   CONFIG   )  
    for key in CONFIG.keys():
        print(key, ":", CONFIG[key], "\n")
    


if __name__ == "__main__":
    main()