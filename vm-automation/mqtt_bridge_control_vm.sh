#!/bin/bash
# MQTT Bridge Control Panel for VM
# Provides easy start/stop/status commands

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SERVICE_NAME="mqtt-bridge"

show_menu() {
    echo -e "${CYAN}"
    echo "========================================================================"
    echo "  MQTT Bridge - Control Panel (VM)"
    echo "========================================================================"
    echo -e "${NC}"
    echo ""
    echo "Choose an option:"
    echo ""
    echo -e "  ${GREEN}1.${NC} Start MQTT Bridge (manual mode)"
    echo -e "  ${GREEN}2.${NC} Install as systemd service (auto-start)"
    echo -e "  ${YELLOW}3.${NC} Start service"
    echo -e "  ${YELLOW}4.${NC} Stop service"
    echo -e "  ${YELLOW}5.${NC} Restart service"
    echo -e "  ${YELLOW}6.${NC} View service status"
    echo -e "  ${YELLOW}7.${NC} View real-time logs"
    echo -e "  ${RED}8.${NC} Disable auto-start"
    echo -e "  ${RED}9.${NC} Uninstall service"
    echo -e "  10. Exit"
    echo ""
    echo -n "Enter choice (1-10): "
}

check_service_installed() {
    if systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
        return 0
    else
        return 1
    fi
}

while true; do
    show_menu
    read choice
    echo ""
    
    case $choice in
        1)
            echo -e "${GREEN}🚀 Starting MQTT Bridge in manual mode...${NC}"
            echo "Press Ctrl+C to stop"
            echo ""
            python3 mqtt_to_influx_bridge_vm.py
            ;;
        2)
            if [ "$EUID" -ne 0 ]; then
                echo -e "${RED}❌ This option requires root privileges${NC}"
                echo "Run: sudo bash mqtt_bridge_control_vm.sh"
            else
                echo -e "${CYAN}📦 Installing as systemd service...${NC}"
                bash install_mqtt_bridge_service_vm.sh
            fi
            ;;
        3)
            if check_service_installed; then
                echo -e "${GREEN}🚀 Starting service...${NC}"
                sudo systemctl start $SERVICE_NAME
                sleep 1
                sudo systemctl status $SERVICE_NAME --no-pager
            else
                echo -e "${RED}❌ Service not installed. Choose option 2 first.${NC}"
            fi
            ;;
        4)
            if check_service_installed; then
                echo -e "${RED}🛑 Stopping service...${NC}"
                sudo systemctl stop $SERVICE_NAME
                echo -e "${GREEN}✅ Service stopped${NC}"
            else
                echo -e "${RED}❌ Service not installed${NC}"
            fi
            ;;
        5)
            if check_service_installed; then
                echo -e "${YELLOW}🔄 Restarting service...${NC}"
                sudo systemctl restart $SERVICE_NAME
                sleep 1
                sudo systemctl status $SERVICE_NAME --no-pager
            else
                echo -e "${RED}❌ Service not installed${NC}"
            fi
            ;;
        6)
            if check_service_installed; then
                echo -e "${YELLOW}📊 Service Status:${NC}"
                sudo systemctl status $SERVICE_NAME --no-pager -l
            else
                echo -e "${RED}❌ Service not installed${NC}"
            fi
            ;;
        7)
            if check_service_installed; then
                echo -e "${YELLOW}📝 Real-time logs (Press Ctrl+C to exit):${NC}"
                echo ""
                sudo journalctl -u $SERVICE_NAME -f
            else
                echo -e "${RED}❌ Service not installed${NC}"
            fi
            ;;
        8)
            if check_service_installed; then
                echo -e "${RED}⚠️  Disabling auto-start...${NC}"
                sudo systemctl disable $SERVICE_NAME
                echo -e "${GREEN}✅ Auto-start disabled${NC}"
            else
                echo -e "${RED}❌ Service not installed${NC}"
            fi
            ;;
        9)
            if check_service_installed; then
                echo -e "${RED}⚠️  Uninstalling service...${NC}"
                sudo systemctl stop $SERVICE_NAME
                sudo systemctl disable $SERVICE_NAME
                sudo rm -f /etc/systemd/system/${SERVICE_NAME}.service
                sudo systemctl daemon-reload
                echo -e "${GREEN}✅ Service uninstalled${NC}"
            else
                echo -e "${RED}❌ Service not installed${NC}"
            fi
            ;;
        10)
            echo -e "${CYAN}👋 Exiting...${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Invalid choice${NC}"
            ;;
    esac
    
    echo ""
    echo -e "${CYAN}========================================================================${NC}"
    echo ""
    read -p "Press Enter to continue..."
    clear
done
