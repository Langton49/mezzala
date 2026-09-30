import { Sidebar } from "../sidebar/Sidebar";
import { MainView } from "../main_view/MainView";

export function DashboardShell(){
    return(
        <div className="h-screen bg-background text-foreground">
            <div className="mx-auto grid h-full max-w-[1200px] grid-cols-[auto_1fr] gap-4 p-4">
                <Sidebar/>
                <MainView/>
            </div>
        </div>
    )
}
