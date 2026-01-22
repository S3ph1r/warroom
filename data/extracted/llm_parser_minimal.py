```python
import pandas as pd

# Definizione dei dati in formato lista di dizionari per facilitare la conversione in DataFrame
data = [
    {'Data': '19-dic-2025', 'TipoOperazione': 'Contrattazione', 'NomeProdotto': 'SolidPowerInc.', 'Tipo': 'Vendi-', 'Quantita': 19, 'ValoreUnitario': 4.52, 'CostoTotale': -1.03},
    {'Data': '18-dic-2025', 'TipoOperazione': 'Contrattazione', 'NomeProdotto': 'Amplifon', 'Tipo': 'Acquista-', 'Quantita': 7, 'ValoreUnitario': 13.98, 'CostoTotale': -2.1},
    {'Data': '17-dic-2025', 'TipoOperazione': 'Contrattazione', 'NomeProdotto': 'AlphabetInc.ClassA', 'Tipo': 'Dividendoincontanti', 'Quantita': 2, 'ValoreUnitario': 0.21, 'CostoTotale': -0.08},
    {'Data': '16-dic-2025', 'TipoOperazione': 'Contrattazione', 'NomeProdotto': 'AlphabetInc.ClassA', 'Tipo': 'Vendi-', 'Quantita': 2, 'ValoreUnitario': 297.89, 'CostoTotale': -2.12},
    {'Data': '15-dic-2025', 'TipoOperazione': 'Contrattazione', 'NomeProdotto': 'EutelsatCommunications-Rights', 'Tipo': 'Opzionecallsutitoliintermedi', 'Quantita': -21.6, 'ValoreUnitario': 0, 'CostoTotale': 0},
    {'Data': '14-dic-2025', 'TipoOperazione': 'Contrattazione', 'NomeProdotto': 'EutelsatCommunications-Rights', 'Tipo': 'VenditaAllachiusura-', 'Quantita': -22, 'ValoreUnitario': 0, 'CostoTotale': 0},
    {'Data': '13-dic-2025', 'TipoOperazione': 'Contrattazione', 'NomeProdotto': 'EutelsatCommunications-Rights', 'Tipo': 'AcquistoInapertura+', 'Quantita': 4, 'ValoreUnitario': 1.35, 'CostoTotale': -5.4},
    {'Data': '12-dic-2025', 'TipoOperazione': 'Contrattazione', 'NomeProdotto': 'BroadcomInc.', 'Tipo': 'Vendi-', 'Quantita': 2, 'ValoreUnitario': 353, 'CostoTotale': -2.35},
    {'Data': '11-dic-2025', 'TipoOperazione': 'Contrattazione', 'NomeProdotto': 'ToyotaMotorCorp.-ADR', 'Tipo': 'Acquista-', 'Quantita': 2, 'ValoreUnitario': 215.81, 'CostoTotale': -1.76},
    {'Data': '10-dic-2025', 'TipoOperazione': 'Trasferimentodiliquidità', 'NomeProdotto': '', 'Tipo': 'Deposito+', 'Quantita': 2000, 'ValoreUnitario': 1, 'CostoTotale': 2000},
    {'Data': '9-dic-2025', 'TipoOperazione': 'Contrattazione', 'NomeProdotto': 'NovoNordiskBA/S', 'Tipo': 'Acquista-', 'Quantita': 4, 'ValoreUnitario': 319.1, 'CostoTotale': -1.77},
    {'Data': '8-dic-2025', 'TipoOperazione': 'Contrattazione', 'NomeProdotto': 'OculusInc.', 'Tipo': 'Vendi-', 'Quantita': 7000, 'ValoreUnitario': 0.05, 'CostoTotale': -15.9},
]

# Conversione dei dati in un DataFrame
df = pd.DataFrame(data)

# Funzione per calcolare il totale delle operazioni di acquisto e vendita
def calculate_total_operations(df):
    total_acquisti = df[df['Tipo'].str.contains('Acquista')]['CostoTotale'].sum()
    total_vendite = df[df['Tipo'].str.contains('Vendi')]['CostoTotale'].sum()

    return {'TotalAcquisti': total_acquisti, 'TotalVendite': total_vendite}

# Calcolo dei totali
total_operations = calculate_total_operations(df)

print(total_operations)
```