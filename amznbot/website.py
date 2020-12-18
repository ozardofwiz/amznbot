class Website:
    def __init__(self, domain_name):
        self.domain_name = domain_name

    def isamazonde(self):
        if self.domain_name == "amazon.de":
            return True
        else:
            return False

    def isamazoncouk(self):
        if self.domain_name == "amazon.co.uk":
            return True
        else:
            return False
