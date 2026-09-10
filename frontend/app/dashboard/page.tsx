import { DashboardProvider, useDashboard } from "@/context/DashboardContext";

export function main(){
    const VBBBB = 1;
    return(
    <div>
        <DashboardProvider children={VBBBB}/>
    </div>
);
}