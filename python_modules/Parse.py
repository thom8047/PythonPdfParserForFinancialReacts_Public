import re
import PyPDF2 as pdf
import json
import datetime as dt
import calendar
import ProjectExceptions


class PDFParser:
    def __init__(self, path=None):
        self.transJSON = open('transaction.json', 'r')
        self.exitProgram = False
        self.path = path

        # INIT Values for parsing
        self.currentPDF = open(self.path, 'rb')
        self.pdfReader = pdf.PdfFileReader(self.currentPDF)
        self.start = False

        # Need an if to check if our json data contains this info
        try:
            self.financialDict = json.load(self.transJSON)
            # used to close and re-open and clear out the json file
            self.transJSON.close()
            self.transJSON = open('transaction.json', 'w')
        except json.JSONDecodeError:
            print("empty file, continue")

    def save(self):
        if (self.checkForDuplicate(self.statement)):
            # Now increment the number of statements
            self.financialDict["transaction_data"]["submissions"] = int(
                self.currentSub)+1

            self.exitProgram = True
            json.dump(self.financialDict, self.transJSON, indent=4)
            self.close()

    def close(self):
        self.transJSON.close()
        # self.currentPDF.close()

    def checkForDuplicate(self, statement):
        numOfOccurances = 0
        for _, value in self.financialDict.items():
            if (value == statement):
                numOfOccurances += 1

        if numOfOccurances != 1:
            self.exit(1)
            return False

        return True

    def exit(self, error=0):
        self.exitProgram = True
        if error == 0:  # this error corresponds to being a copy
            error_message = "\nError Code: 0\nStatement has already been uploaded, please upload different file...\n"
            self.financialDict.pop(f"Statement{self.currentSub}")
        # this error corresponds to being a copy, but finding out after reading file.
        elif error == 1:
            error_message = "\nError Code: 1\nStatement has been read, but was found to be a duplicate afterwards.\n"
            self.financialDict.pop(f"Statement{self.currentSub}")
        # this error corresponds to a transaction object not conforming. (Error in write func/missing data)
        elif error == 2:
            error_message = "\nError Code: 2\ntransaction did not conform to specified shape.\n"
            self.financialDict.pop(f"Statement{self.currentSub}")
        print(error_message)
        json.dump(self.financialDict, self.transJSON, indent=4)
        self.close()

    def getYear(self, date, from_year, to_year):
        try:
            [month, day] = date.split("/")
            if not (int(to_year) - int(from_year)):
                return f"/{from_year}"
            else:
                if (month == "12"):
                    return f"/{from_year}"
                else:
                    # print(f"made it to this year -> /{to_year}")
                    return f"/{to_year}"
        except Exception as e:
            return f"/{from_year}"


class PDFCheckingAndSavingsParser(PDFParser):
    def isIncome(self, string):
        incomeKeyWords = ["Zelle From", "Payroll", "Venmo Cashout",
                          "Online Transfer From", "Overdraft Protection From", "Direct Dep",
                          "Semantic Arts", "Vaed Treas", "Interest Payment", "Deposit", "Wells Fargo Rewards"]
        for key in incomeKeyWords:
            if (key.lower() in string.lower()):
                return True
        return False

    def isDate(self, dateArray):
        # Meant to check what is a date
        month, day = dateArray
        try:
            if (int(month)) and (int(day)):
                return True

        except ValueError:
            return False

    def setDate(self, endDateList, end=False):
        # Month / Day / Year
        [month, day, year] = endDateList

        day = day.replace(",", "")

        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]

        for imonth in range(12):
            if (end):

                if months[imonth] == month:
                    month = imonth+1

                    return f"{month}/{day}/{year}"
            elif not (end):
                if months[imonth] == month:
                    if (imonth == 0):
                        year -= 1
                        month = 12
                    else:
                        month = imonth

                    # Adjust the day after figuring month and possibly year
                    day = int(day) + 1

                    try:
                        start_date = dt.datetime(
                            int(year), int(month), int(day))
                        return f"{month}/{day}/{year}"
                    except ValueError:
                        return f"{month}/{calendar.monthrange(int(year), int(month))[1]}/{year}"

    def parseAll(self):
        for page in range(self.pdfReader.getNumPages()):
            self.parse(page)

    def parse(self, pageNum=0):
        if self.exitProgram:
            return
        parsedAgain = False if not pageNum else True

        pageObj = self.pdfReader.getPage(pageNum)
        text = pageObj.extractText()
        iterTrack = 0
        transHistStart = 0
        accountNumIteration = -1
        checkingDateIteration = 1

        # Now lets config transaction data and add in new statement on first parse
        if not parsedAgain:
            self.currentSub = self.financialDict["transaction_data"]["submissions"]
            self.currentAcc = self.financialDict["transaction_data"]["accounts"]
            self.financialDict[f"Statement{self.currentSub}"] = {}
            self.statement = self.financialDict[f"Statement{self.currentSub}"]
            self.statement["ACCOUNTNUMBER"] = ""
            self.statement["FROM"] = ""
            self.statement["TO"] = ""
            self.statement["transaction"] = []

        for line in text.split('\n'):
            if self.exitProgram:
                break

            if ("Account number: " in line):
                accountNumIteration = iterTrack+1
            if (accountNumIteration == iterTrack):
                self.statement["ACCOUNTNUMBER"] = f"Ending in {line[-4:]}"
                if not (f"Ending in {line[-4:]}" in self.currentAcc):
                    self.currentAcc.append(f"Ending in {line[-4:]}")

            try:
                if (iterTrack == checkingDateIteration):
                    endDate = line.split(" ")[:3]
                    if not (endDate.count("")):
                        self.statement["FROM"] = self.setDate(endDate, False)
                        self.statement["TO"] = self.setDate(endDate, True)

                        for key, value in self.financialDict.items():
                            if (key == "transaction_data") or (key == f"Statement{self.currentSub}"):
                                continue
                            if value["TO"] == self.statement["TO"] and value.ACCOUNTNUMBER == self.statement["ACCOUNTNUMBER"]:
                                # remove our current statement dictionary and exit program
                                self.exit(0)
                                break
            except:
                checkingDateIteration = 2

            if (("Ending balance on" in line) and (transHistStart)):
                self.write(text.split('\n')[transHistStart+1:iterTrack])
                self.save()
                break
            if ("Transaction history" in line):
                transHistStart = iterTrack
            if (("Sheet Seq" in line) and (transHistStart)):
                self.write(text.split('\n')[transHistStart+1:iterTrack])
                break
            if ((iterTrack == len(text.split('\n'))-1) and (transHistStart)):
                self.write(text.split('\n')[transHistStart+1:iterTrack])
                break

            iterTrack += 1

    def write(self, transactions):
        obj, diff = {}, 0

        # Remove the headers/titles of transactions
        if ("balance" in transactions[9]):
            transactions = transactions[10:]
        elif ("balance" in transactions[10]):
            transactions = transactions[11:]
        elif ("balance" in transactions[7]):
            transactions = transactions[8:]

        for info in transactions:
            if (diff == -1):
                if obj:
                    if (len(obj) != 3):
                        raise ProjectExceptions.NonConformedTransactionObject(
                            f"Error: Object is not what we expect...")
                    # Now we have our transaction from prev iterations
                    self.statement["transaction"].append(obj)

            if (len(info.split('/')) == 2) and (self.isDate(info.split('/'))):
                obj, diff = {}, 0

                year = self.getYear(info, self.statement["FROM"].split(
                    "/")[2], self.statement["TO"].split("/")[2])

                obj["TRANS_DATE"] = info + year
            elif (diff == 1):
                try:
                    if int(info):
                        # This is a check
                        pass
                except ValueError:
                    # This is not a check and this is the beginning of description
                    obj["DESCR"] = info
            elif (diff == 2):
                if (info == "Check"):
                    obj["DESCR"] = info
                else:
                    try:
                        regex = re.compile(r"(\d),(\d)")
                        if regex.search(info):
                            info = info.replace(",", "")
                        if (float(info)):
                            # Check if description contains our income key words

                            if (self.isIncome(obj["DESCR"])):
                                # For testing
                                # obj["DESCR"]
                                obj["INCOME"] = info
                            else:
                                obj["CHARGE"] = info

                            # We have our last bit of information, No point to keep going. This may have caused errors
                            diff = -2
                    except ValueError:
                        # Must be more description
                        obj["DESCR"] += info
            elif (diff == 3):
                try:
                    if obj["CHARGE"]:
                        # We have a charge in our object and this float is our ending balance
                        break
                except KeyError:
                    try:
                        # We have an income in our object and this float is our ending balance
                        if obj["INCOME"]:
                            break

                    except KeyError:
                        try:
                            regex = re.compile(r"(\d),(\d)")
                            if regex.search(info):
                                info = info.replace(",", "")
                            if (float(info)):
                                # Check if description contains our income key words
                                if (self.isIncome(obj["DESCR"])):
                                    obj["INCOME"] = info
                                else:
                                    obj["CHARGE"] = info

                                # We have our last bit of information, No point to keep going.
                                diff = -2
                        except ValueError:
                            # Must be more description
                            obj["DESCR"] += info

            elif (diff == 4):
                try:
                    regex = re.compile(r"(\d),(\d)")
                    if regex.search(info):
                        info = info.replace(",", "")
                    if (float(info)):
                        # Check if description contains our income key words
                        if (self.isIncome(obj["DESCR"])):
                            obj["INCOME"] = info
                        else:
                            obj["CHARGE"] = info

                        # We have our last bit of information, No point to keep going.
                        diff = -2
                except ValueError:
                    # Don't know what this is. We can add more detail as situations arise
                    if (len(obj) == 1 or 2):
                        obj = {}
                        continue
                    else:
                        raise ProjectExceptions.UnknownParsedValue(
                            f"Error: don't know what this error is...")

            diff += 1

            # Thought I needed some extra code to add the last stateent, but now we have a check in place
            # for when our transaction object is complete and this code is obsolete. I will keep until I'm
            # sure this isn;t an issue.
            #
            # if obj != {}:
            #     # Now we have our transaction from prev iterations
            #     self.statement["transaction"].append(obj)


class PDFCreditParser(PDFParser):
    def parseAgain(self):
        for page in range(self.pdfReader.getNumPages()):
            if not (page):
                pass
            else:
                self.parse(page)

    def parse(self, pageNum=0):
        parsedAgain = False if not pageNum else True

        pageObj = self.pdfReader.getPage(pageNum)
        text = pageObj.extractText()
        iterTrack = 0
        transHistStart = 0

        # Now lets config transaction data and add in new statement on first parse
        if not parsedAgain:
            self.currentSub = self.financialDict["transaction_data"]["submissions"]
            self.currentAcc = self.financialDict["transaction_data"]["accounts"]
            self.financialDict[f"Statement{self.currentSub}"] = {}
            self.statement = self.financialDict[f"Statement{self.currentSub}"]

        for line in text.split('\n'):
            if self.exitProgram:
                break

            if (iterTrack == 2 and not parsedAgain):
                self.statement["ACCOUNTNUMBER"] = line
                if not (line in self.currentAcc):
                    self.currentAcc.append(line)

            if (iterTrack == 4 and not parsedAgain):
                _from, to = line.split(' ')[0], line.split(' ')[2]
                for key, value in self.financialDict.items():
                    if (key == "transaction_data") or (key == f"Statement{self.currentSub}"):
                        continue
                    if value["FROM"] == _from and value["ACCOUNTNUMBER"] == self.statement["ACCOUNTNUMBER"]:
                        # remove our current statement dictionary and exit program

                        self.exit(0)
                        break
                self.statement["FROM"] = _from
                self.statement["TO"] = to

            if ("TOTAL PURCHASES, BALANCE TRANSFERS & OTHER CHARGES FOR THIS PERIOD" in line):
                self.write(text.split('\n')[transHistStart+1:iterTrack])
                self.save()
                break
            if ("Purchases, Balance Transfers & Other Charges" in line):
                transHistStart = iterTrack
                self.start = True
            if ("Detach and mail with check payable to" in line):
                if (self.start):
                    self.write(text.split('\n')[transHistStart+1:iterTrack])
                    self.parseAgain()
                    break
                else:
                    self.parseAgain()
                    break

            iterTrack += 1

    def write(self, transac):
        count = 0
        transDictionary = {}
        descrList = []

        self.statement["transaction"] = [] if not (
            "transaction" in self.statement.keys()) else self.statement["transaction"]

        for index in range(len(transac)-1):
            element = transac[index]
            # print(element, transDictionary)

            year = self.getYear(element, self.statement["FROM"].split(
                "/")[2], self.statement["TO"].split("/")[2]) or ""

            if count == 0:
                # Should be trans date
                try:
                    dt.datetime.strptime(element, "%m/%d")
                    transDictionary["TRANS_DATE"] = element + year
                    count += 1
                    continue
                except Exception:
                    pass
                    # Exception casght and date is not valid. This should not be the case but how do we account for it?
                    # transDictionary["TRANS_DATE"] = ""
            elif count == 1:
                # Should be post date
                try:
                    dt.datetime.strptime(element, "%m/%d")
                    transDictionary["POST_DATE"] = element + year
                    count += 1
                    continue
                except Exception:
                    pass
                    # Exception caught and date is not valid. This should not be the case but how do we account for it?
                    # transDictionary["TRANS_DATE"] = ""
            elif count == 2:
                # Should be reference_id (no spaces)
                try:
                    if re.search("\s", element):
                        raise ValueError("Space was found in Ref#")
                    transDictionary["REF_ID"] = element
                    count += 1
                    continue
                except Exception:
                    pass
                    # Exception caught, invalid ref #
            elif count == 3:
                # Should be description
                descrList.append(element)
                count += 1
                continue
            elif count == 4:
                # Should be float (if not it's description and redo) | if float, make count 0 again
                try:
                    if (float(element)):
                        transDictionary["CHARGE"] = element
                        transDictionary["DESCR"] = "".join(descrList)
                        self.statement["transaction"].append(
                            transDictionary)

                        if ("TRANS_DATE" in transDictionary.keys() and "POST_DATE" in transDictionary.keys(
                        ) and "REF_ID" in transDictionary.keys() and "DESCR" in transDictionary.keys() and "CHARGE" in transDictionary.keys()):
                            pass
                            # Everything conforms
                        else:
                            self.exit(2)

                        # reset
                        descrList = []
                        transDictionary = {}
                        count = 0
                except Exception as finalerror:
                    descrList.append(element)
