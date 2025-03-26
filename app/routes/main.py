from flask import Blueprint, render_template, redirect, url_for, flash, current_app
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Redirect to upload page"""
    return redirect(url_for('files.upload'))

@main_bp.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok'} 