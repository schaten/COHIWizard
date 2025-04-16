import sys
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox

class DateTimeDifferenceCalculator(QDialog):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Date and Time Difference Calculator")
        
        self.date_label1 = QLabel("Enter the first date and time (YYYY-MM-DD HH:MM:SS)")
        self.date_entry1 = QLineEdit()
        self.date_label2 = QLabel("Enter the second date and time (YYYY-MM-DD HH:MM:SS)")
        self.date_entry2 = QLineEdit()
        self.calculate_button = QPushButton("Calculate")
        self.calculate_button.clicked.connect(self.calculate_difference)
        
        layout = QVBoxLayout()
        layout.addWidget(self.date_label1)
        layout.addWidget(self.date_entry1)
        layout.addWidget(self.date_label2)
        layout.addWidget(self.date_entry2)
        layout.addWidget(self.calculate_button)
        self.setLayout(layout)
        
    def calculate_difference(self):
        date1 = self.date_entry1.text()
        date2 = self.date_entry2.text()
        try:
            # convert the input strings to datetime objects
            datetime1 = datetime.strptime(date1, "%Y-%m-%d %H:%M:%S")
            datetime2 = datetime.strptime(date2, "%Y-%m-%d %H:%M:%S")
            # calculate the difference between the two datetime objects
            delta = datetime2 - datetime1
            # show the difference in days, seconds, microseconds
            QMessageBox.information(self, "Difference", f"Difference: {delta.days} day(s), {delta.seconds} second(s), {delta.microseconds} microsecond(s)")
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid date and time format. Please enter in YYYY-MM-DD HH:MM:SS format.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    calculator = DateTimeDifferenceCalculator()
    calculator.show()
    sys.exit(app.exec_())