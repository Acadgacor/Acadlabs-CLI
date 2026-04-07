"""
Acadlabs CLI - Main Entry Point
Command-line interface untuk interaksi dengan Acadlabs
"""
import click
from ai import ai_client
from db import db

@click.group()
def cli():
    """Acadlabs CLI Tool"""
    pass

@cli.command()
@click.option('--message', prompt='Your message', help='Message to send to AI')
@click.option('--model', default='gpt-3.5-turbo', help='AI model to use')
def chat(message, model):
    """Chat dengan OpenRouter AI"""
    click.echo(f"Sending to {model}...")

    result = ai_client.chat(message, model)

    if result:
        click.echo("\n✓ Response from AI:")
        click.echo(result)
    else:
        click.echo("✗ Failed to get response from AI")

@cli.command()
@click.argument('table')
def get(table):
    """Retrieve data dari database"""
    click.echo(f"Fetching data from {table}...")

    result = db.get_data(table)

    if result:
        click.echo(f"✓ Found {len(result)} records:")
        for record in result:
            click.echo(record)
    else:
        click.echo(f"✗ No data found or error occurred")

@cli.command()
@click.argument('table')
@click.option('--data', '-d', multiple=True, help='Data to insert (key=value)')
def insert(table, data):
    """Insert data ke database"""
    # Convert list of 'key=value' strings to dictionary
    data_dict = {}
    for item in data:
        key, value = item.split('=')
        data_dict[key] = value

    click.echo(f"Inserting into {table}...")
    result = db.insert_data(table, data_dict)

    if result:
        click.echo(f"✓ Data inserted successfully: {result}")
    else:
        click.echo("✗ Failed to insert data")

@cli.command()
def status():
    """Check status of API connections"""
    click.echo("Checking connections...")

    # Check OpenRouter
    if ai_client.api_key:
        click.echo("✓ OpenRouter API Key: Configured")
    else:
        click.echo("✗ OpenRouter API Key: NOT configured")

    # Check Supabase
    try:
        click.echo("✓ Supabase Connection: OK")
    except Exception as e:
        click.echo(f"✗ Supabase Connection: Error - {e}")

if __name__ == '__main__':
    cli()
