import unittest
from unittest.mock import patch, MagicMock
import parser

class TestParser(unittest.TestCase):

    @patch("parser.webdriver.Chrome")      # Мокаем Chrome
    @patch("parser.WebDriverWait")         # Мокаем WebDriverWait
    def test_parse_plan_returns_data(self, mock_wait, mock_chrome):
        # Мокаем драйвер
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        # Мокаем WebDriverWait.until так, чтобы возвращал table_body
        mock_table_body = MagicMock()

        # Мокаем одну строку таблицы с дисциплиной
        mock_row = MagicMock()
        # ячейки таблицы: [name, ..., sem_hours1, sem_hours2, sem_hours3, ctrl1, ctrl2]
        mock_cell_name = MagicMock(); mock_cell_name.text = "Математика"
        mock_cell_hours1 = MagicMock(); mock_cell_hours1.text = "10"
        mock_cell_hours2 = MagicMock(); mock_cell_hours2.text = "5"
        mock_cell_hours3 = MagicMock(); mock_cell_hours3.text = "0"
        mock_cell_control1 = MagicMock(); mock_cell_control1.text = "+"
        mock_cell_control2 = MagicMock(); mock_cell_control2.text = ""

        # В зависимости от semester, функция get_cells_by_semester берёт индексы 9:14 (1 семестр)
        mock_row.find_elements.return_value = [
            mock_cell_name, MagicMock(), MagicMock(), MagicMock(), MagicMock(),
            MagicMock(), MagicMock(), MagicMock(), MagicMock(),
            mock_cell_hours1, mock_cell_hours2, mock_cell_hours3, mock_cell_control1, mock_cell_control2
        ]
        mock_table_body.find_elements.return_value = [mock_row]

        mock_wait.return_value.until.return_value = mock_table_body

        # Вызываем parse_plan
        data = parser.parse_plan("testlogin", "testpass", 1)

        # Проверяем, что возвращается список со словарем и правильными ключами
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        self.assertIn("name", data[0])
        self.assertIn("hours", data[0])
        self.assertIn("type", data[0])
        self.assertIn("semester", data[0])
        self.assertIn("login", data[0])

    def test_log_returns_none(self):
        result = parser.log("Test message")
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
