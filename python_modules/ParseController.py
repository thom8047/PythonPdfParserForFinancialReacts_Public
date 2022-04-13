from Parse import PDFCheckingAndSavingsParser, PDFCreditParser
import os

if __name__ == "__main__":
    checkingDir, creditDir = ["C:/Users/kedwa/Desktop/statements/checking/",
                              "C:/Users/kedwa/Desktop/statements/credit/"]

    for file in os.listdir(creditDir):
        pathway = creditDir+file
        obj = PDFCreditParser(pathway)
        obj.parse()

    for file in os.listdir(checkingDir):
        pathway = checkingDir+file
        obj = PDFCheckingAndSavingsParser(pathway)
        obj.parseAll()
