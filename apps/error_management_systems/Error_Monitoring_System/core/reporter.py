from config.systems import SYSTEMS_CONFIG
from models.system_stats import SystemStats

def create_professional_system_html_with_trends(system_name, data, stats, date_str, trends_data=None):
    """Creates a professional HTML report enriched with trend analysis and explanatory text."""
    
    # Define color mappings and text
    status_colors = {
        'HEALTHY': ('#27ae60', '✅ SYSTEM HEALTHY'),
        'WARNING': ('#f39c12', '⚠️ SYSTEM WARNING'),
        'CRITICAL': ('#e74c3c', '🔴 SYSTEM CRITICAL'),
        'NO_DATA': ('#95a5a6', '⚪ NO DATA')
    }

    trend_colors = {
        'IMPROVING': ('#27ae60', '📈 IMPROVING'),
        'DEGRADING': ('#e74c3c', '📉 DEGRADING'),
        'STABLE': ('#3498db', '➡️ STABLE')
    }

    momentum_colors = {
        'ACCELERATING': '#e74c3c',
        'DECELERATING': '#27ae60',
        'NEUTRAL': '#3498db',
        'INSUFFICIENT_DATA': '#95a5a6'
    }

    stability_colors = {
        'HIGH_VOLATILITY': '#e74c3c',
        'MODERATE': '#f39c12',
        'STABLE': '#27ae60',
        'INSUFFICIENT_DATA': '#95a5a6'
    }

    # Get status color and text based on the stats dictionary
    status_color, status_text = status_colors.get(stats['status'], status_colors['NO_DATA'])

    # Trend analysis section HTML
    trend_section = ""
    if trends_data and trends_data.get('days_analyzed', 0) >= 2:
        trend_status = stats.get('trend_status', 'STABLE')
        trend_color, trend_text = trend_colors.get(trend_status, trend_colors['STABLE'])
        trend_arrow = '⬇️' if stats.get('error_trend', 0) < 0 else '⬆️' if stats.get('error_trend', 0) > 0 else '➡️'
        
        # Determine momentum and stability info
        momentum = trends_data.get('momentum', 'INSUFFICIENT_DATA')
        momentum_color = momentum_colors.get(momentum, momentum_colors['INSUFFICIENT_DATA'])
        
        stability = trends_data.get('stability_trend', 'INSUFFICIENT_DATA')
        stability_color = stability_colors.get(stability, stability_colors['INSUFFICIENT_DATA'])
        
        prediction_text = f"{stats.get('predicted_errors', 0)} errors ({stats.get('prediction_confidence', 'LOW')} confidence)"

        trend_section = f"""
        <div class="trend-analysis">
            <h3>{trend_arrow} Trend Analysis (Last days)</h3>
            <div class="trend-grid">
                <div class="trend-item"><strong>Current Trend:</strong> <span style="color: {trend_color}; font-weight: bold;">{trend_text}</span></div>
                <div class="trend-item"><strong>Error Change (Day-1):</strong> <span style="color: {trend_color};">{stats.get('error_trend', 0):+d}</span> ({stats.get('improvement_rate', 0):+.1f}%)</div>
                <div class="trend-item"><strong>7-Day Avg Trend:</strong> <span style="color: {trend_color};">{trends_data.get('week_trend', 0):+.1f} avg</span></div>
                <div class="trend-item"><strong>Momentum:</strong> <span style="color: {momentum_color}; font-weight: bold;">{momentum.replace('_', ' ')}</span></div>
                <div class="trend-item"><strong>Volatility:</strong> <span style="color: {stability_color}; font-weight: bold;">{stability.replace('_', ' ')}</span></div>
                <div class="trend-item"><strong>Predicted Errors Tomorrow:</strong> <span style="color: {momentum_colors.get(momentum, 'black')};">{prediction_text}</span></div>
            </div>
        </div>
        """
    
    # Determine recommendation text based on status and trends
    recommendation_list = []
    if stats['status'] == 'CRITICAL':
        recommendation_list.append(f"<li>🚨 Immediate action is required. Investigate the <strong>{stats.get('critical_services', 0)} critical services</strong> to identify and resolve the root cause of high error counts.</li>")
    if stats['status'] == 'WARNING' and stats['affected_services'] > 0:
        recommendation_list.append(f"<li>⚠️ The system is showing signs of instability. Prioritize the <strong>{stats.get('affected_services', 0)} affected services</strong> for analysis.</li>")
    if stats.get('trend_status') == 'DEGRADING':
        recommendation_list.append(f"<li>📉 The number of errors is increasing. Analyze the cause of the degradation trend and implement preventative measures.</li>")
    if stats.get('stability_trend') == 'HIGH_VOLATILITY':
        recommendation_list.append(f"<li>📊 The system is highly volatile. Monitor error peaks and investigate services with erratic behavior.</li>")
    if stats.get('momentum') == 'ACCELERATING':
        recommendation_list.append(f"<li>🔥 Error growth is accelerating. A swift intervention is crucial to prevent the situation from becoming critical.</li>")
    if not recommendation_list:
        recommendation_list.append("<li>✅ The system is stable and healthy. Continue to monitor and perform routine maintenance to ensure long-term reliability.</li>")

    recommendation_html = "".join(recommendation_list)

    # HTML for affected and critical service lists
    affected_services_html = "<p>No affected services.</p>"
    if stats.get('affected_services_list'):
        affected_services_html = "<ul>" + "".join([f"<li>{service}</li>" for service in stats['affected_services_list']]) + "</ul>"

    critical_services_html = "<p>No critical services.</p>"
    if stats.get('critical_services_list'):
        critical_services_html = "<ul>" + "".join([f"<li style='color: #e74c3c; font-weight: bold;'>{service}</li>" for service in stats['critical_services_list']]) + "</ul>"

    # Return the complete HTML document as a single string
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{system_name} - System Health Report</title>
        <style>
            body {{ 
                font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #2d3748;
            }}
            .container {{ 
                max-width: 1200px; 
                margin: 20px auto; 
                background: rgba(255, 255, 255, 0.95); 
                border-radius: 24px; 
                backdrop-filter: blur(20px);
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(255, 255, 255, 0.1);
                overflow: hidden;
            }}
            .header {{ 
                background: linear-gradient(145deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05)); 
                color: #1a202c; 
                padding: 50px 40px; 
                text-align: center; 
                position: relative;
                overflow: hidden;
            }}
            .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M30 30c0-11.046-8.954-20-20-20s-20 8.954-20 20 8.954 20 20 20 20-8.954 20-20zM0 0h20v20H0V0zm40 40h20v20H40V40z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E") repeat;
                opacity: 0.1;
            }}
            .header h1 {{ 
                font-size: 2.8rem; 
                margin: 0 0 15px; 
                font-weight: 800; 
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                position: relative;
                z-index: 1;
            }}
            .header p {{
                position: relative;
                z-index: 1;
                font-size: 1.1rem;
                opacity: 0.9;
            }}
            .status-badge {{ 
                background: {status_color}; 
                color: white; 
                padding: 14px 28px; 
                border-radius: 50px; 
                font-weight: 700; 
                margin-top: 20px; 
                display: inline-block;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.2);
                position: relative;
                z-index: 1;
            }}
            .content {{ 
                padding: 50px; 
                line-height: 1.6; 
            }}
            .intro {{ 
                background: linear-gradient(145deg, #f7fafc, #edf2f7);
                padding: 30px; 
                border-radius: 18px; 
                margin-bottom: 30px;
                box-shadow: 
                    12px 12px 24px #d1d9e6,
                    -12px -12px 24px #ffffff,
                    inset 1px 1px 3px rgba(255,255,255,0.8);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            .intro h2 {{ margin-top: 0; color: #2c3e50; }}
            
            /* Styles pour les cartes d'indicateurs clés - une seule ligne responsive */
            .stats-grid {{ 
                display: flex; 
                flex-wrap: wrap;
                gap: 15px; 
                margin: 30px 0; 
                justify-content: space-between;
            }}
            .stat-card {{ 
                background: linear-gradient(135deg, #f8f9fa, #e9ecef); 
                padding: 20px; 
                border-radius: 12px; 
                text-align: center; 
                border-left: 4px solid #3498db; 
                transition: transform 0.2s;
                flex: 1;
                min-width: 150px;
                max-width: 180px;
            }}
            .stat-card:hover {{ transform: translateY(-5px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            .stat-number {{ font-size: 2rem; font-weight: 700; color: #2c3e50; margin-bottom: 8px; }}
            .stat-label {{ font-size: 0.8rem; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
            
            /* Styles pour les métriques avancées - une seule ligne responsive */
            .advanced-stats-grid {{ 
                display: flex; 
                flex-wrap: wrap;
                gap: 20px; 
                margin: 30px 0; 
                justify-content: space-between;
            }}
            .advanced-stat-card {{ 
                background: linear-gradient(135deg, #f8f9fa, #e9ecef); 
                padding: 25px; 
                border-radius: 12px; 
                text-align: center; 
                transition: transform 0.2s;
                flex: 1;
                min-width: 200px;
                max-width: 280px;
            }}
            .advanced-stat-card:hover {{ transform: translateY(-5px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            
            /* Media queries pour la responsivité */
            @media (max-width: 1200px) {{
                .stats-grid {{
                    justify-content: center;
                }}
                .stat-card {{
                    min-width: 130px;
                    max-width: 160px;
                }}
                .advanced-stats-grid {{
                    justify-content: center;
                }}
                .advanced-stat-card {{
                    min-width: 180px;
                    max-width: 250px;
                }}
            }}
            
            @media (max-width: 768px) {{
                .stats-grid {{
                    flex-direction: column;
                    align-items: center;
                }}
                .stat-card {{
                    max-width: 300px;
                    width: 100%;
                }}
                .advanced-stats-grid {{
                    flex-direction: column;
                    align-items: center;
                }}
                .advanced-stat-card {{
                    max-width: 300px;
                    width: 100%;
                }}
            }}
            
            .danger {{ color: #e74c3c !important; }}
            .success {{ color: #27ae60 !important; }}
            .warning {{ color: #f39c12 !important; }}
            .recommendations {{ background: linear-gradient(135deg, #d4edda, #c3e6cb); color: #155724; padding: 30px; border-radius: 12px; margin: 30px 0; border: 1px solid #c3e6cb; }}
            .recommendations h3 {{ margin-bottom: 20px; font-size: 1.4rem; color: #155724; }}
            .recommendations ul {{ padding-left: 20px; }}
            .recommendations li {{ margin-bottom: 10px; font-weight: 500; }}
            .footer {{ background: #2c3e50; color: white; padding: 25px; text-align: center; }}
            .trend-info {{ font-size: 1.1rem; margin-bottom: 10px; }}
            .service-lists-container {{ display: flex; justify-content: space-around; gap: 30px; margin-top: 30px; }}
            .service-list-card {{ flex: 1; background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
            .service-list-card h4 {{ margin-top: 0; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }}
            .service-list-card ul {{ list-style-type: none; padding: 0; margin: 0; }}
            .service-list-card li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
            .service-list-card li:last-child {{ border-bottom: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>System {system_name}</h1>
                <p>Advanced Error Analysis Report - {date_str}</p>
                <div class="status-badge">{status_text}</div>
            </div>
            
            <div class="content">
                <div class="intro">
                    <h2>🔎 Report Objective</h2>
                    <p>
                        This report provides a detailed analysis of the errors and incidents encountered on the
                        <strong>{system_name}</strong> system. You will find a summary of the key indicators,
                        the observed trends, as well as recommendations to improve stability
                        and reduce the impact on your services.
                    </p>
                    <p>
                        The objective is to provide you with a clear vision of the system's health status,
                        to facilitate decision-making and the implementation of corrective or preventive actions.
                    </p>
                </div>
                
                {trend_section}

                <h2>📊 Key Indicators</h2>
                <p>
                    The figures below summarize the current state of the system.
                    They allow for a quick identification of the volume of errors, the number of affected services,
                    and the overall health level.
                </p>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number {'danger' if stats['total_errors'] > 0 else 'success'}">{stats.get('total_errors', 0)}</div>
                        <div class="stat-label">Total Errors</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{stats.get('total_services', 0)}</div>
                        <div class="stat-label">Total Services</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'danger' if stats['affected_services'] > 0 else 'success'}">{stats.get('affected_services', 0)}</div>
                        <div class="stat-label">Affected Services</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'danger' if stats['critical_services'] > 0 else 'success'}">{stats.get('critical_services', 0)}</div>
                        <div class="stat-label">Critical Services</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'warning' if stats['avg_errors'] > 2 else 'success'}">{stats.get('avg_errors', 0)}</div>
                        <div class="stat-label">Avg Errors/Service</div>
                    </div>
                </div>

                <h2>📈 Advanced Metrics & Insights</h2>
                <div class="advanced-stats-grid">
                <div class="advanced-stat-card" style="border-left: 4px solid #f1c40f;">
                        <div class="stat-number">{stats.get('top_error_service', 'N/A')}</div>
                        <div class="stat-label">Top Error Service</div>
                    </div>
                    <div class="advanced-stat-card" style="border-left: 4px solid #e67e22;">
                        <div class="stat-number">
                            <span class="{stats.get('risk_level', '').lower()}">{stats.get('risk_level', 'N/A')}</span>
                        </div>
                        <div class="stat-label">Risk Level</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {'success' if stats['health_percentage'] > 80 else 'warning' if stats['health_percentage'] > 60 else 'danger'}">{stats.get('health_percentage', 0)}%</div>
                        <div class="stat-label">Health Rate</div>
                    </div>
                    <div class="advanced-stat-card" style="border-left: 4px solid #2ecc71;">
                        <div class="stat-number {'success' if stats.get('stability_index', 0) > 70 else 'warning' if stats.get('stability_index', 0) > 50 else 'danger'}">{stats.get('stability_index', 0)}</div>
                        <div class="stat-label">Stability Index (0-100)</div>
                    </div>
                </div>
                
                <h2>📋 Service Details</h2>
                <p>
                    Below are the lists of services currently impacted. These lists provide a quick overview of which services require immediate attention.
                </p>
                <div class="service-lists-container">
                    <div class="service-list-card">
                        <h4 style="color: #f39c12;">Services Affected ({stats.get('affected_services', 0)})</h4>
                        {affected_services_html}
                    </div>
                    <div class="service-list-card">
                        <h4 style="color: #e74c3c;">Critical Services ({stats.get('critical_services', 0)})</h4>
                        {critical_services_html}
                    </div>
                </div>
                
                <div class="recommendations">
                    <h3>🎯 Strategic Insights & Action Plan</h3>
                    <p>
                        Here is an interpretation of the results and actions to consider to improve the situation.
                        Please collaborate with the monitoring team to identify the root causes
                        and implement effective solutions.
                    </p>
                    <ul>
                        {recommendation_html}
                    </ul>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>Enhanced MTN Monitoring System</strong> | Generated: {date_str}</p>
                <p>📧 For urgent issues: Contact monitoring team immediately</p>
            </div>
        </div>
    </body>
    </html>
    """

def create_executive_summary_html_with_trends(systems_data, all_stats, date_str):
    """Enhanced version of the executive summary with trends and Soft UI design"""
    
    # Global calculations
    total_errors = sum(stats.get('total_errors', 0) for stats in all_stats.values())
    total_services_monitored = sum(stats.get('total_services', 0) for stats in all_stats.values())
    improving_systems = sum(1 for stats in all_stats.values() if stats.get('error_trend', 0) < 0)
    degrading_systems = sum(1 for stats in all_stats.values() if stats.get('error_trend', 0) > 0)
    
    total_affected_services = sum(len(stats.get('affected_services_list', [])) for stats in all_stats.values())
    total_critical_services = sum(len(stats.get('critical_services_list', [])) for stats in all_stats.values())
    
    # Global status with trend
    if degrading_systems > improving_systems:
        global_status = "📉 SYSTEMS DEGRADING"
        global_class = "warning"
    elif improving_systems > 0:
        global_status = "📈 SYSTEMS IMPROVING"
        global_class = "success"
    else:
        global_status = "➡️ SYSTEMS STABLE"
        global_class = "info"
        
    # --- Collect lists for detailed sections ---
    # Top 5 degrading services
    all_trends = []
    for system_name, stats in all_stats.items():
        if stats.get('data') is not None and not stats['data'].empty:
            # Check for error_trend and previous_errors to calculate degradation
            current_errors = stats.get('total_errors', 0)
            previous_errors = stats.get('previous_errors', 0)
            if current_errors > previous_errors:
                degradation_amount = current_errors - previous_errors
                all_trends.append({'system': system_name, 'errors': degradation_amount})

    top_degrading_systems = sorted(all_trends, key=lambda x: x['errors'], reverse=True)[:5]
    
    top_degrading_html = ""
    if top_degrading_systems:
        top_degrading_html = "<ul>" + "".join([f"<li><strong>{d['system']}</strong>: +{d['errors']} errors</li>" for d in top_degrading_systems]) + "</ul>"
    else:
        top_degrading_html = "<p>No degrading systems identified.</p>"
    
    # Global critical services list
    all_critical_services_list = []
    for system_name, stats in all_stats.items():
        for service in stats.get('critical_services_list', []):
            all_critical_services_list.append(f"<strong>{system_name}</strong>: {service}")

    critical_services_html = ""
    if all_critical_services_list:
        critical_services_html = "<ul>" + "".join([f"<li>🚨 {s}</li>" for s in all_critical_services_list]) + "</ul>"
    else:
        critical_services_html = "<p>No critical services found across all systems. Excellent!</p>"

    # --- Start HTML Generation ---
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ 
                font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #2d3748;
            }}
            .container {{ 
                max-width: 1400px; 
                margin: 20px auto; 
                background: rgba(255, 255, 255, 0.95); 
                border-radius: 24px; 
                backdrop-filter: blur(20px);
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(255, 255, 255, 0.1);
                overflow: hidden;
            }}
            
            .header {{ 
                background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05)); 
                color: #1a202c; 
                padding: 60px 50px; 
                text-align: center; 
                position: relative;
                overflow: hidden;
            }}
            .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M30 30c0-11.046-8.954-20-20-20s-20 8.954-20 20 8.954 20 20 20 20-8.954 20-20zM0 0h20v20H0V0zm40 40h20v20H40V40z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E") repeat;
                opacity: 0.1;
            }}
            .header h1 {{ 
                font-size: 3.2rem; 
                margin: 0 0 15px; 
                font-weight: 800; 
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                position: relative;
                z-index: 1;
            }}
            .header p {{
                position: relative;
                z-index: 1;
            }}
            
            .global-status {{ 
                padding: 16px 32px; 
                border-radius: 50px; 
                font-weight: 700; 
                margin-top: 25px; 
                display: inline-block;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.2);
                position: relative;
                z-index: 1;
            }}
            
            .content {{ 
                padding: 50px; 
            }}
            
            /* Soft UI Trend Summary avec cartes en ligne */
            .trend-summary {{ 
                background: linear-gradient(145deg, #ffffff, #f7fafc);
                border-radius: 20px; 
                padding: 40px; 
                margin: 30px 0;
                box-shadow: 
                    20px 20px 60px #d1d9e6, 
                    -20px -20px 60px #ffffff,
                    inset 2px 2px 5px rgba(255,255,255,0.8),
                    inset -2px -2px 5px rgba(0,0,0,0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
            .trend-summary h3 {{
                margin: 0 0 30px 0; 
                font-size: 1.8rem;
                font-weight: 700;
                color: #2d3748;
                text-align: center;
                text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
            }}
            
            /* Grid pour les métriques en une ligne responsive */
            .trend-metrics-grid {{ 
                display: flex;
                flex-wrap: wrap;
                gap: 20px; 
                justify-content: space-between;
            }}
            .trend-metric-card {{ 
                flex: 1;
                min-width: 160px;
                max-width: 200px;
                text-align: center;
                padding: 25px 20px;
                background: linear-gradient(145deg, #f7fafc, #edf2f7);
                border-radius: 16px;
                box-shadow: 
                    6px 6px 12px #d1d9e6,
                    -6px -6px 12px #ffffff,
                    inset 1px 1px 2px rgba(255,255,255,0.8);
                transition: all 0.3s ease;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            .trend-metric-card:hover {{
                transform: translateY(-3px);
                box-shadow: 
                    8px 8px 16px #d1d9e6,
                    -8px -8px 16px #ffffff,
                    inset 2px 2px 4px rgba(255,255,255,0.9);
            }}
            .trend-metric-number {{
                font-size: 2.2rem; 
                font-weight: 800;
                color: #4a5568;
                text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
                margin-bottom: 8px;
            }}
            .trend-metric-label {{
                font-size: 0.9rem;
                color: #718096;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            /* Media queries pour la responsivité */
            @media (max-width: 1200px) {{
                .trend-metrics-grid {{
                    justify-content: center;
                }}
                .trend-metric-card {{
                    min-width: 140px;
                    max-width: 180px;
                }}
            }}
            @media (max-width: 768px) {{
                .trend-metrics-grid {{
                    flex-direction: column;
                    align-items: center;
                }}
                .trend-metric-card {{
                    max-width: 280px;
                    width: 100%;
                }}
            }}
            
            .systems-grid {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); 
                gap: 30px; 
                margin: 40px 0; 
            }}
            .system-card {{ 
                background: linear-gradient(145deg, #ffffff, #f7fafc);
                border-radius: 20px; 
                padding: 30px; 
                box-shadow: 
                    15px 15px 30px #d1d9e6, 
                    -15px -15px 30px #ffffff,
                    inset 1px 1px 3px rgba(255,255,255,0.8);
                transition: all 0.3s ease;
                border: 1px solid rgba(255, 255, 255, 0.2);
                position: relative;
                overflow: hidden;
            }}
            .system-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #667eea, #764ba2);
                border-radius: 20px 20px 0 0;
            }}
            .system-card:hover {{ 
                transform: translateY(-8px); 
                box-shadow: 
                    20px 20px 40px #d1d9e6, 
                    -20px -20px 40px #ffffff,
                    inset 2px 2px 5px rgba(255,255,255,0.9);
            }}
            .system-name {{ 
                font-size: 1.4rem; 
                font-weight: 700; 
                margin-bottom: 20px; 
                color: #2d3748;
                text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
            }}
            .trend-indicator {{ 
                font-size: 1rem; 
                margin: 15px 0; 
                padding: 10px 18px; 
                border-radius: 25px; 
                display: inline-block;
                font-weight: 600;
                box-shadow: inset 2px 2px 5px rgba(0,0,0,0.1), inset -2px -2px 5px rgba(255,255,255,0.8);
            }}
            .improving {{ 
                background: linear-gradient(145deg, #c6f6d5, #9ae6b4); 
                color: #22543d; 
            }}
            .degrading {{ 
                background: linear-gradient(145deg, #fed7d7, #feb2b2); 
                color: #742a2a; 
            }}
            .stable {{ 
                background: linear-gradient(145deg, #bee3f8, #90cdf4); 
                color: #2a4365; 
            }}
            .danger {{ color: #e53e3e; }}
            .success {{ color: #38a169; }}
            .warning {{ color: #d69e2e; }}
            .info {{ 
                color: #2b6cb0; 
                background: linear-gradient(145deg, #bee3f8, #90cdf4);
                box-shadow: inset 2px 2px 5px rgba(0,0,0,0.1), inset -2px -2px 5px rgba(255,255,255,0.8);
            }}
            
            .footer {{ 
                background: linear-gradient(145deg, #2d3748, #1a202c);
                color: black; 
                padding: 40px; 
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            .footer::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(45deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
            }}
            .footer p {{
                position: relative;
                z-index: 1;
                text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
            }}
            
            .list-section {{ 
                display: flex; 
                justify-content: space-between; 
                gap: 30px; 
                margin-top: 40px; 
            }}
            .list-card {{ 
                flex: 1; 
                background: linear-gradient(145deg, #f7fafc, #edf2f7);
                padding: 30px; 
                border-radius: 18px; 
                box-shadow: 
                    12px 12px 24px #d1d9e6,
                    -12px -12px 24px #ffffff,
                    inset 1px 1px 3px rgba(255,255,255,0.8);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            .list-card h4 {{ 
                margin-top: 0; 
                color: #2d3748; 
                border-bottom: 2px solid rgba(102, 126, 234, 0.2);
                padding-bottom: 15px;
                text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
                font-weight: 700;
            }}
            .list-card ul {{ 
                list-style-type: none; 
                padding: 0; 
                margin: 0; 
            }}
            .list-card li {{ 
                padding: 12px 0; 
                border-bottom: 1px solid rgba(0,0,0,0.05);
                font-size: 1rem;
                transition: all 0.2s ease;
            }}
            .list-card li:hover {{
                padding-left: 10px;
                color: #667eea;
            }}
            .list-card li:last-child {{ 
                border-bottom: none; 
            }}
            
            .recommendations {{
                background: linear-gradient(145deg, #fff5f5, #fed7d7);
                padding: 40px; 
                border-radius: 20px; 
                margin: 40px 0;
                box-shadow: 
                    15px 15px 30px #d1d9e6,
                    -15px -15px 30px #ffffff,
                    inset 1px 1px 3px rgba(255,255,255,0.8);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            .recommendations h3 {{
                font-size: 1.6rem; 
                margin-bottom: 25px;
                color: #742a2a;
                text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
                font-weight: 700;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Executive Dashboard</h1>
                <p style="font-size: 1.3rem; opacity: 0.9; font-weight: 500;">All Systems Performance & Evolution Analysis</p>
                <p style="font-size: 1.1rem; opacity: 0.8;">{date_str}</p>
                <div class="global-status {global_class}">{global_status}</div>
            </div>
            
            <div class="content">
                <div class="trend-summary">
                    <h3>📈 Global Trend Analysis</h3>
                    <div class="trend-metrics-grid">
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #38a169;">{improving_systems}</div>
                            <div class="trend-metric-label">Systems Improving</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #e53e3e;">{degrading_systems}</div>
                            <div class="trend-metric-label">Systems Degrading</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #d69e2e;">{total_affected_services}</div>
                            <div class="trend-metric-label">Affected Services</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #e53e3e;">{total_critical_services}</div>
                            <div class="trend-metric-label">Critical Services</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #2b6cb0;">{total_errors}</div>
                            <div class="trend-metric-label">Total Errors</div>
                        </div>
                        <div class="trend-metric-card">
                            <div class="trend-metric-number" style="color: #4a5568;">{total_services_monitored}</div>
                            <div class="trend-metric-label">Services Monitored</div>
                        </div>
                    </div>
                </div>
                
                <h2 style="color: #2d3748; margin: 50px 0 30px; font-size: 2rem; font-weight: 700; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">🖥️ Systems Performance Dashboard</h2>
                <div class="systems-grid">
    """
    
    # Adding system cards with trends
    for system_name, stats in all_stats.items():
        error_trend = stats.get('error_trend', 0)
        trend_class = 'improving' if error_trend < 0 else 'degrading' if error_trend > 0 else 'stable'
        trend_text = f'📈 -{abs(error_trend)} errors' if error_trend < 0 else f'📉 +{error_trend} errors' if error_trend > 0 else '➡️ No change'
        
        html += f"""
                    <div class="system-card">
                        <h3 class="system-name">{system_name} System</h3>
                        <div class="trend-indicator {trend_class}">
                            {trend_text} vs yesterday
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0;">
                            <div style="text-align: center; padding: 15px; background: linear-gradient(145deg, #edf2f7, #e2e8f0); border-radius: 12px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                                <div style="font-size: 1.6rem; font-weight: 800; color: {'#e53e3e' if stats.get('total_errors', 0) > 0 else '#38a169'}; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">{stats.get('total_errors', 0)}</div>
                                <div style="font-size: 0.9rem; color: #718096; font-weight: 600;">Current Errors</div>
                            </div>
                            <div style="text-align: center; padding: 15px; background: linear-gradient(145deg, #edf2f7, #e2e8f0); border-radius: 12px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                                <div style="font-size: 1.6rem; font-weight: 800; color: #4a5568; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">{stats.get('health_percentage', 0):.1f}%</div>
                                <div style="font-size: 0.9rem; color: #718096; font-weight: 600;">Health Rate</div>
                            </div>
                        </div>
                        <div style="margin-top: 20px; font-size: 0.95rem; color: #4a5568; line-height: 1.6;">
                            <div style="margin-bottom: 8px;">Critical Services: <span style="font-weight: 700; color: {'#e53e3e' if stats.get('critical_services', 0) > 0 else '#38a169'};">{stats.get('critical_services', 0)}</span></div>
                            <div style="margin-bottom: 8px;">Most Impacted: <span style="font-weight: 700; color: #667eea;">{stats.get('top_error_service', 'N/A')}</span></div>
                            {f'<div>Weekly Trend: <span style="font-weight: 700; color: #764ba2;">{stats.get("improvement_rate", 0):+.1f}%</span></div>' if 'improvement_rate' in stats else ''}
                        </div>
                    </div>
        """
    
    html += f"""
                </div>
                
                <h2 style="color: #2d3748; margin: 50px 0 30px; font-size: 2rem; font-weight: 700; text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);">❗ Actionable Insights</h2>
                <div class="list-section">
                    <div class="list-card">
                        <h4 style="color: #e53e3e;">Top 5 Degrading Systems ({len(top_degrading_systems)})</h4>
                        {top_degrading_html}
                    </div>
                    <div class="list-card">
                        <h4 style="color: #e53e3e;">Global Critical Services ({len(all_critical_services_list)})</h4>
                        {critical_services_html}
                    </div>
                </div>

                <div class="recommendations">
                    <h3>🎯 Strategic Recommendations</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 30px;">
                        <div style="background: linear-gradient(145deg, #ffffff, #f7fafc); padding: 25px; border-radius: 16px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                            <h4 style="color: #742a2a; margin-bottom: 15px; font-size: 1.2rem;">⚡ Immediate Actions:</h4>
                            <ul style="margin: 0; padding-left: 20px; color: #2d3748;">
                                {'<li style="margin-bottom: 8px;">Investigate degrading systems immediately</li>' if degrading_systems > 0 else '<li style="margin-bottom: 8px;">Maintain current monitoring practices</li>'}
                                {'<li style="margin-bottom: 8px;">Replicate improvement strategies across systems</li>' if improving_systems > 0 else '<li style="margin-bottom: 8px;">Review error prevention measures</li>'}
                                <li style="margin-bottom: 8px;">Focus on critical services requiring attention</li>
                            </ul>
                        </div>
                        <div style="background: linear-gradient(145deg, #ffffff, #f7fafc); padding: 25px; border-radius: 16px; box-shadow: inset 3px 3px 6px #d1d9e6, inset -3px -3px 6px #ffffff;">
                            <h4 style="color: #742a2a; margin-bottom: 15px; font-size: 1.2rem;">📊 Strategic Insights:</h4>
                            <ul style="margin: 0; padding-left: 20px; color: #2d3748;">
                                <li style="margin-bottom: 8px;">Track daily trends to identify patterns</li>
                                <li style="margin-bottom: 8px;">Implement predictive maintenance where possible</li>
                                <li style="margin-bottom: 8px;">Document successful improvement strategies</li>
                                <li style="margin-bottom: 8px;">Plan capacity upgrades for consistently problematic services</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p style="font-size: 1.2rem; font-weight: 700; margin-bottom: 10px;"><strong>🚀 Advanced MTN Systems Monitoring</strong></p>
                <p style="font-size: 1rem; margin-bottom: 10px;">📈 Trend Analysis • 📊 Performance Tracking • ⚡ Real-time Insights</p>
                <p style="font-size: 0.9rem; opacity: 0.9;">Generated: {date_str} | Next Analysis: Tomorrow</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html