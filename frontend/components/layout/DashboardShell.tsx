import { Sidebar } from "../sidebar/Sidebar";
import { MainView } from "../main_view/MainView";

export function DashboardShell(){
    return(
        <div className="grid h-screen grid-cols-[auto_1fr] bg-background text-foreground">
            <Sidebar/>
            <MainView/>
        </div>
    )
}
